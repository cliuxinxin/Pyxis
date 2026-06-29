"""Agent execution primitive."""

from __future__ import annotations

from dataclasses import dataclass, field

from pyxis.memory import Memory, NoMemory
from pyxis.providers import CompletionRequest, MockProvider, Provider
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

    def run(self, prompt: str, *, context: dict | None = None) -> AgentResult:
        request = CompletionRequest(
            prompt=prompt,
            instructions=self.instructions,
            context={"agent": self.name, **(context or {})},
        )
        result = self.provider.complete(request)
        return AgentResult(output=result.output, raw=result.raw, metadata=result.metadata)

    def get_tool(self, name: str) -> Tool | None:
        return next((tool for tool in self.tools if tool.name == name), None)
