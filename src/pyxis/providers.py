"""Model provider abstractions."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pyxis.errors import (
    ProviderCancelledError,
    ProviderConfigurationError,
    ProviderRequestError,
    ProviderTimeoutError,
)


class CancellationToken:
    """Simple cancellation token shared with provider calls."""

    def __init__(self) -> None:
        self._cancelled = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True

    def throw_if_cancelled(self) -> None:
        if self._cancelled:
            raise ProviderCancelledError("Provider request was cancelled.")


@dataclass(frozen=True)
class CompletionRequest:
    """Provider-agnostic completion request."""

    prompt: str
    instructions: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    timeout: float | None = None
    cancellation_token: CancellationToken | None = None


@dataclass(frozen=True)
class CompletionResult:
    """Provider-agnostic completion result."""

    output: str
    raw: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] | None = None
    finish_reason: str | None = None


@dataclass(frozen=True)
class CompletionChunk:
    """A provider-native streaming chunk."""

    text: str
    raw: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] | None = None
    finish_reason: str | None = None


class Provider(Protocol):
    """Protocol implemented by model providers."""

    def complete(self, request: CompletionRequest) -> CompletionResult:
        ...


class MockProvider:
    """Predictable provider for local development and tests."""

    def __init__(self, output: str | None = None) -> None:
        self.output = output
        self.requests: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> CompletionResult:
        _throw_if_cancelled(request)
        self.requests.append(request)
        output = self.output
        if output is None:
            output = f"{request.instructions}\n{request.prompt}".strip()
        return CompletionResult(
            output=output,
            metadata={"provider": "mock", "finish_reason": "stop"},
            finish_reason="stop",
        )


class OpenAICompatibleProvider:
    """Provider for OpenAI-compatible chat completions APIs."""

    def __init__(
        self,
        *,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 60,
        temperature: float | None = None,
        max_retries: int = 0,
        backoff: float = 0.5,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.model = model
        configured_base_url = base_url or os.getenv("OPENAI_BASE_URL") or ""
        self.base_url = configured_base_url.rstrip("/")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.timeout = timeout
        self.temperature = temperature
        self.max_retries = max_retries
        self.backoff = backoff
        self.extra_headers = dict(extra_headers or {})

    def complete(self, request: CompletionRequest) -> CompletionResult:
        _throw_if_cancelled(request)
        if not self.base_url:
            raise ProviderConfigurationError(
                "OpenAICompatibleProvider requires base_url or OPENAI_BASE_URL."
            )
        if not self.api_key:
            raise ProviderConfigurationError(
                "OpenAICompatibleProvider requires api_key or OPENAI_API_KEY."
            )

        payload = self._build_payload(request)
        response = self._post_json("/chat/completions", payload, request=request)
        output = self._extract_output(response)
        finish_reason = self._extract_finish_reason(response)
        usage = response.get("usage") if isinstance(response.get("usage"), dict) else None
        return CompletionResult(
            output=output,
            raw=response,
            metadata={
                "provider": "openai-compatible",
                "model": self.model,
                "usage": usage,
                "finish_reason": finish_reason,
            },
            usage=usage,
            finish_reason=finish_reason,
        )

    def stream(self, request: CompletionRequest) -> Iterator[CompletionChunk]:
        _throw_if_cancelled(request)
        if not self.base_url:
            raise ProviderConfigurationError(
                "OpenAICompatibleProvider requires base_url or OPENAI_BASE_URL."
            )
        if not self.api_key:
            raise ProviderConfigurationError(
                "OpenAICompatibleProvider requires api_key or OPENAI_API_KEY."
            )

        payload = self._build_payload(request)
        payload["stream"] = True
        yield from self._post_stream("/chat/completions", payload, request=request)

    def _build_payload(self, request: CompletionRequest) -> dict[str, Any]:
        messages: list[dict[str, str]] = []
        if request.instructions:
            messages.append({"role": "system", "content": request.instructions})
        messages.append({"role": "user", "content": request.prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        return payload

    def _post_json(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        request: CompletionRequest,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers,
        }
        http_request = Request(url, data=body, headers=headers, method="POST")

        data = self._send_with_retries(http_request, request=request)

        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ProviderRequestError("Provider returned invalid JSON.") from exc

        if not isinstance(parsed, dict):
            raise ProviderRequestError("Provider returned a non-object JSON response.")
        return parsed

    def _post_stream(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        request: CompletionRequest,
    ) -> Iterator[CompletionChunk]:
        url = f"{self.base_url}{path}"
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            **self.extra_headers,
        }
        http_request = Request(url, data=body, headers=headers, method="POST")

        try:
            with self._open_stream_with_retries(http_request, request=request) as response:
                for event_data in self._iter_sse_data(response, request=request):
                    if event_data == "[DONE]":
                        break
                    yield self._parse_stream_chunk(event_data)
        except TimeoutError as exc:
            raise ProviderTimeoutError("Provider stream timed out.") from exc
        except URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise ProviderTimeoutError("Provider stream timed out.") from exc
            raise ProviderRequestError(f"Provider stream failed: {exc.reason}") from exc

    def _open_stream_with_retries(
        self,
        http_request: Request,
        *,
        request: CompletionRequest,
    ):
        attempts = self.max_retries + 1
        last_error: Exception | None = None

        for attempt in range(attempts):
            _throw_if_cancelled(request)
            try:
                timeout = request.timeout if request.timeout is not None else self.timeout
                return urlopen(http_request, timeout=timeout)
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if exc.code < 500 or attempt == attempts - 1:
                    raise ProviderRequestError(
                        f"Provider stream failed with HTTP {exc.code}: {detail}"
                    ) from exc
                last_error = exc
            except URLError as exc:
                if attempt == attempts - 1:
                    if isinstance(exc.reason, TimeoutError):
                        raise ProviderTimeoutError("Provider stream timed out.") from exc
                    raise ProviderRequestError(f"Provider stream failed: {exc.reason}") from exc
                last_error = exc
            except TimeoutError as exc:
                if attempt == attempts - 1:
                    raise ProviderTimeoutError("Provider stream timed out.") from exc
                last_error = exc

            if self.backoff > 0:
                _throw_if_cancelled(request)
                time.sleep(self.backoff * (2**attempt))

        raise ProviderRequestError(f"Provider stream failed: {last_error}") from last_error

    def _iter_sse_data(
        self,
        response,
        *,
        request: CompletionRequest,
    ) -> Iterator[str]:
        event_lines: list[str] = []
        for raw_line in response:
            _throw_if_cancelled(request)
            line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
            if not line:
                if event_lines:
                    yield "\n".join(event_lines)
                    event_lines = []
                continue
            if not line.startswith("data:"):
                continue
            event_lines.append(line.removeprefix("data:").strip())
        if event_lines:
            yield "\n".join(event_lines)

    def _parse_stream_chunk(self, data: str) -> CompletionChunk:
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ProviderRequestError("Provider stream returned invalid JSON.") from exc

        if not isinstance(parsed, dict):
            raise ProviderRequestError("Provider stream returned a non-object JSON chunk.")

        try:
            choice = parsed["choices"][0]
            delta = choice.get("delta", {})
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderRequestError("Provider stream chunk did not include choices.") from exc
        if delta is None:
            delta = {}
        if not isinstance(delta, dict):
            raise ProviderRequestError("Provider stream chunk delta was not an object.")

        text = delta.get("content") or ""
        finish_reason = choice.get("finish_reason")
        usage = parsed.get("usage") if isinstance(parsed.get("usage"), dict) else None

        return CompletionChunk(
            text=text,
            raw=parsed,
            metadata={
                "provider": "openai-compatible",
                "model": self.model,
                "usage": usage,
                "finish_reason": finish_reason,
            },
            usage=usage,
            finish_reason=finish_reason,
        )

    def _send_with_retries(
        self,
        http_request: Request,
        *,
        request: CompletionRequest,
    ) -> str:
        attempts = self.max_retries + 1
        last_error: Exception | None = None

        for attempt in range(attempts):
            _throw_if_cancelled(request)
            try:
                timeout = request.timeout if request.timeout is not None else self.timeout
                with urlopen(http_request, timeout=timeout) as response:
                    return response.read().decode("utf-8")
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if exc.code < 500 or attempt == attempts - 1:
                    raise ProviderRequestError(
                        f"Provider request failed with HTTP {exc.code}: {detail}"
                    ) from exc
                last_error = exc
            except URLError as exc:
                if attempt == attempts - 1:
                    raise ProviderRequestError(
                        f"Provider request failed after {attempts} attempt(s): {exc.reason}"
                    ) from exc
                last_error = exc
            except TimeoutError as exc:
                if attempt == attempts - 1:
                    raise ProviderTimeoutError(
                        f"Provider request timed out after {attempts} attempt(s)."
                    ) from exc
                last_error = exc

            if self.backoff > 0:
                _throw_if_cancelled(request)
                time.sleep(self.backoff * (2**attempt))

        raise ProviderRequestError(f"Provider request failed: {last_error}") from last_error

    def _extract_output(self, response: dict[str, Any]) -> str:
        try:
            output = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderRequestError(
                "Provider response did not include message content."
            ) from exc

        if not isinstance(output, str):
            raise ProviderRequestError("Provider message content was not a string.")
        return output

    def _extract_finish_reason(self, response: dict[str, Any]) -> str | None:
        try:
            finish_reason = response["choices"][0].get("finish_reason")
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderRequestError(
                "Provider response did not include a valid choice."
            ) from exc
        return finish_reason if isinstance(finish_reason, (str, type(None))) else None


def _throw_if_cancelled(request: CompletionRequest) -> None:
    if request.cancellation_token is not None:
        request.cancellation_token.throw_if_cancelled()
