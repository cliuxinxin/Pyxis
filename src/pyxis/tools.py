"""Tool wrappers for Python callables."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any

from pyxis.errors import ToolExecutionError
from pyxis.results import ToolResult
from pyxis.types import JsonDict, RiskLevel


@dataclass(frozen=True)
class ToolCall:
    """A pending or executed tool invocation."""

    name: str
    args: tuple[Any, ...] = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)
    risk: RiskLevel = "low"
    action: str = "tool_call"


@dataclass(frozen=True)
class Tool:
    """A callable capability exposed to an agent."""

    name: str
    fn: Callable[..., Any]
    description: str = ""
    risk: RiskLevel = "low"
    action: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def manifest(self) -> JsonDict:
        """Return the tool information exposed to an agent."""

        return {
            "name": self.name,
            "description": self.description,
            "risk": self.risk,
            "action": self.action or "tool_call",
        }

    def __call__(self, *args: Any, **kwargs: Any) -> ToolResult:
        try:
            output = self.fn(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - exact exception is user code.
            raise ToolExecutionError(f"Tool {self.name!r} failed: {exc}") from exc
        return ToolResult(
            name=self.name,
            output=output,
            requires_confirmation=False,
            metadata={"risk": self.risk, **self.metadata},
        )


def tool(
    fn: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    risk: RiskLevel = "low",
    action: str | None = None,
    **metadata: Any,
):
    """Decorate a Python callable as a Pyxis tool."""

    def decorate(func: Callable[..., Any]) -> Tool:
        return Tool(
            name=name or func.__name__,
            fn=func,
            description=description or (func.__doc__ or "").strip(),
            risk=risk,
            action=action,
            metadata=metadata,
        )

    if fn is None:
        return decorate

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return fn(*args, **kwargs)

    return decorate(wrapper)
