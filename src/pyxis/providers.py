"""Model provider abstractions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


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
