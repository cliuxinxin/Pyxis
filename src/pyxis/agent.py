"""Agent execution primitive."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field

from pyxis.actions import build_action_instructions
from pyxis.dialogue import ResponseStyle
from pyxis.memory import Memory, NoMemory
from pyxis.providers import CancellationToken, CompletionRequest, MockProvider, Provider
from pyxis.results import AgentResult
from pyxis.tools import Tool


@dataclass
class Agent:
    """A role-bound execution body with tools, memory, and a provider."""

    name: str
    instructions: str = ""
    provider: Provider = field(default_factory=MockProvider)
    tools: list[Tool] = field(default_factory=list)
    memory: Memory = field(default_factory=NoMemory)
    response_style: ResponseStyle = field(default_factory=ResponseStyle)

    def run(
        self,
        prompt: str,
        *,
        context: dict | None = None,
        timeout: float | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> AgentResult:
        request = self.completion_request(
            prompt,
            context=context,
            timeout=timeout,
            cancellation_token=cancellation_token,
        )
        result = self.provider.complete(request)
        return AgentResult(
            output=self.response_style.apply(result.output),
            raw=result.raw,
            metadata=result.metadata,
        )

    async def arun(
        self,
        prompt: str,
        *,
        context: dict | None = None,
        timeout: float | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> AgentResult:
        request = self.completion_request(
            prompt,
            context=context,
            timeout=timeout,
            cancellation_token=cancellation_token,
        )
        acomplete = getattr(self.provider, "acomplete", None)
        if callable(acomplete):
            result = acomplete(request)
            if inspect.isawaitable(result):
                result = await result
        else:
            result = self.provider.complete(request)
        return AgentResult(
            output=self.response_style.apply(result.output),
            raw=result.raw,
            metadata=result.metadata,
        )

    def stream(
        self,
        prompt: str,
        *,
        context: dict | None = None,
        timeout: float | None = None,
        cancellation_token: CancellationToken | None = None,
    ):
        stream = getattr(self.provider, "stream", None)
        if not callable(stream):
            raise TypeError(f"Provider for agent {self.name!r} does not support streaming.")
        yield from stream(
            self.completion_request(
                prompt,
                context=context,
                timeout=timeout,
                cancellation_token=cancellation_token,
            )
        )

    def completion_request(
        self,
        prompt: str,
        *,
        context: dict | None = None,
        timeout: float | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> CompletionRequest:
        return CompletionRequest(
            prompt=prompt,
            instructions=self.system_instructions(),
            context={"agent": self.name, **(context or {})},
            timeout=timeout,
            cancellation_token=cancellation_token,
        )

    def get_tool(self, name: str) -> Tool | None:
        return next((tool for tool in self.tools if tool.name == name), None)

    def tool_manifest(self) -> list[dict]:
        return [tool.manifest() for tool in self.tools]

    def action_instructions(self) -> str:
        return build_action_instructions(self.tool_manifest())

    def system_instructions(self) -> str:
        parts = [part for part in [self.instructions, self.action_instructions()] if part]
        return "\n\n".join(parts)
