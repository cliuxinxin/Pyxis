"""Agent action parsing."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pyxis.types import JsonDict


class AgentActionType(str, Enum):
    """Actions an agent can request from Pyxis."""

    MESSAGE = "message"
    TOOL_CALL = "tool_call"
    STOP = "stop"


@dataclass(frozen=True)
class AgentAction:
    """A parsed action requested by an agent response."""

    type: AgentActionType
    content: str = ""
    tool: str | None = None
    args: tuple[Any, ...] = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)
    raw: Any = None


def parse_agent_action(output: str) -> AgentAction:
    """Parse a minimal JSON action protocol from model output.

    Non-JSON output, malformed JSON, or unknown action shapes are treated as
    normal messages. This keeps the protocol opt-in and avoids surprising users.
    """

    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return AgentAction(type=AgentActionType.MESSAGE, content=output, raw=output)

    if not isinstance(parsed, dict):
        return AgentAction(type=AgentActionType.MESSAGE, content=output, raw=parsed)

    action_type = parsed.get("type")
    if action_type == AgentActionType.TOOL_CALL.value:
        tool = parsed.get("tool")
        args = parsed.get("args", {})
        if not isinstance(tool, str):
            return AgentAction(type=AgentActionType.MESSAGE, content=output, raw=parsed)
        if isinstance(args, dict):
            return AgentAction(
                type=AgentActionType.TOOL_CALL,
                tool=tool,
                kwargs=args,
                raw=parsed,
            )
        if isinstance(args, list):
            return AgentAction(
                type=AgentActionType.TOOL_CALL,
                tool=tool,
                args=tuple(args),
                raw=parsed,
            )
        return AgentAction(type=AgentActionType.MESSAGE, content=output, raw=parsed)

    if action_type == AgentActionType.STOP.value:
        content = parsed.get("content", "Stopped.")
        return AgentAction(
            type=AgentActionType.STOP,
            content=content if isinstance(content, str) else "Stopped.",
            raw=parsed,
        )

    content = parsed.get("content")
    if action_type == AgentActionType.MESSAGE.value and isinstance(content, str):
        return AgentAction(type=AgentActionType.MESSAGE, content=content, raw=parsed)

    return AgentAction(type=AgentActionType.MESSAGE, content=output, raw=parsed)


def build_action_instructions(tool_manifests: list[JsonDict]) -> str:
    """Build instructions that teach an agent how to request Pyxis actions."""

    if not tool_manifests:
        return ""

    lines = [
        "Pyxis can execute tools through a controlled action protocol.",
        "When you need a tool, respond with only a JSON object in this shape:",
        '{"type":"tool_call","tool":"tool_name","args":{"arg_name":"value"}}',
        "Available tools:",
    ]
    for manifest in tool_manifests:
        description = manifest.get("description") or "No description provided."
        action = manifest.get("action") or "tool_call"
        risk = manifest.get("risk") or "low"
        lines.append(
            f"- {manifest['name']}: {description} "
            f"(risk={risk}, action={action})"
        )

    lines.extend(
        [
            "Use normal text when no tool is needed.",
            "High-risk tools may pause for human confirmation before execution.",
        ]
    )
    return "\n".join(lines)
