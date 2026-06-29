"""Model provider abstractions."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pyxis.errors import ProviderConfigurationError, ProviderRequestError


@dataclass(frozen=True)
class CompletionRequest:
    """Provider-agnostic completion request."""

    prompt: str
    instructions: str = ""
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CompletionResult:
    """Provider-agnostic completion result."""

    output: str
    raw: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


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
        self.requests.append(request)
        output = self.output
        if output is None:
            output = f"{request.instructions}\n{request.prompt}".strip()
        return CompletionResult(output=output, metadata={"provider": "mock"})


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
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.model = model
        configured_base_url = base_url or os.getenv("OPENAI_BASE_URL") or ""
        self.base_url = configured_base_url.rstrip("/")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.timeout = timeout
        self.temperature = temperature
        self.extra_headers = dict(extra_headers or {})

    def complete(self, request: CompletionRequest) -> CompletionResult:
        if not self.base_url:
            raise ProviderConfigurationError(
                "OpenAICompatibleProvider requires base_url or OPENAI_BASE_URL."
            )
        if not self.api_key:
            raise ProviderConfigurationError(
                "OpenAICompatibleProvider requires api_key or OPENAI_API_KEY."
            )

        payload = self._build_payload(request)
        response = self._post_json("/chat/completions", payload)
        output = self._extract_output(response)
        return CompletionResult(
            output=output,
            raw=response,
            metadata={"provider": "openai-compatible", "model": self.model},
        )

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

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers,
        }
        request = Request(url, data=body, headers=headers, method="POST")

        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ProviderRequestError(
                f"Provider request failed with HTTP {exc.code}: {detail}"
            ) from exc
        except URLError as exc:
            raise ProviderRequestError(f"Provider request failed: {exc.reason}") from exc

        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ProviderRequestError("Provider returned invalid JSON.") from exc

        if not isinstance(parsed, dict):
            raise ProviderRequestError("Provider returned a non-object JSON response.")
        return parsed

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
