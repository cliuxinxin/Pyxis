"""Result objects returned by Pyxis operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pyxis.checkpoint import Checkpoint


@dataclass(frozen=True)
class AgentResult:
    """A response produced by an agent."""

    output: str
    raw: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    """A response produced by a tool."""

    name: str
    output: Any = None
    requires_confirmation: bool = False
    checkpoint: Checkpoint | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowResult:
    """A response produced by a workflow."""

    name: str
    output: Any
    steps: list[str] = field(default_factory=list)
    paused: bool = False
    checkpoint: Checkpoint | None = None
    current_step: int | None = None
    state: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NavigationResult:
    """The result of one conversational navigation turn."""

    output: str
    decision: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StreamEvent:
    """A high-level event yielded by session streaming."""

    type: str
    data: dict[str, Any] = field(default_factory=dict)
