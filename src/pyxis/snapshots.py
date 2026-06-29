"""Snapshot persistence helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from pyxis.checkpoint import Checkpoint, CheckpointStatus
from pyxis.dialogue import Clarification, Dialogue, Intent, IntentType, Message, UserGoal
from pyxis.errors import SnapshotRestoreError
from pyxis.events import Event, EventLog, EventType
from pyxis.memory import Memory, ProjectContext, SessionMemory, UserPreferences
from pyxis.providers import MockProvider, Provider
from pyxis.serialization import DEFAULT_REDACT_KEYS, redact_jsonable
from pyxis.tools import Tool, ToolCall
from pyxis.workflow import Workflow

SNAPSHOT_SCHEMA_VERSION = 1
SNAPSHOT_KIND = "pyxis.session"


@dataclass(frozen=True)
class SnapshotMetadata:
    """Version metadata stored with every Pyxis session snapshot."""

    kind: str = SNAPSHOT_KIND
    schema_version: int = SNAPSHOT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class SnapshotRedactionPolicy:
    """Redaction policy for exported snapshots."""

    redact_keys: set[str] = field(default_factory=lambda: set(DEFAULT_REDACT_KEYS))
    replacement: str = "[REDACTED]"

    @classmethod
    def default(cls) -> SnapshotRedactionPolicy:
        return cls()

    def apply(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        redacted = redact_jsonable(
            snapshot,
            redact_keys=set(self.redact_keys),
            replacement=self.replacement,
        )
        return redacted if isinstance(redacted, dict) else {}


@dataclass
class SnapshotRestoreCatalog:
    """Registered callables and runtime objects used to restore a snapshot."""

    tools: dict[str, Tool] = field(default_factory=dict)
    workflows: dict[str, Workflow] = field(default_factory=dict)
    provider: Provider | None = None
    memory: Memory | None = None
    instructions: str = ""

    def register_tool(self, tool: Tool) -> SnapshotRestoreCatalog:
        self.tools[tool.name] = tool
        return self

    def register_workflow(self, workflow: Workflow) -> SnapshotRestoreCatalog:
        self.workflows[workflow.name] = workflow
        return self


def save_snapshot(snapshot: dict[str, Any], path: str | Path) -> Path:
    """Save a JSON-safe session snapshot to disk."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


def load_snapshot(path: str | Path) -> dict[str, Any]:
    """Load a saved session snapshot from disk."""

    loaded = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Snapshot file must contain a JSON object.")
    return loaded


def snapshot_metadata(snapshot: dict[str, Any]) -> SnapshotMetadata:
    """Return snapshot metadata, defaulting legacy snapshots to schema v1."""

    metadata = snapshot.get("metadata")
    if metadata is None:
        return SnapshotMetadata()
    data = _require_dict(metadata, "metadata")
    kind = data.get("kind") or SNAPSHOT_KIND
    if not isinstance(kind, str):
        raise SnapshotRestoreError("Snapshot field metadata.kind must be a string.")
    try:
        schema_version = int(data.get("schema_version") or SNAPSHOT_SCHEMA_VERSION)
    except (TypeError, ValueError) as exc:
        message = "Snapshot field metadata.schema_version must be an integer."
        raise SnapshotRestoreError(message) from exc
    return SnapshotMetadata(kind=kind, schema_version=schema_version)


def restore_session(
    snapshot: dict[str, Any],
    *,
    catalog: SnapshotRestoreCatalog | None = None,
):
    """Restore a session snapshot using an explicit callable catalog."""

    from pyxis.agent import Agent
    from pyxis.session import PendingWorkflow, Session

    metadata = snapshot_metadata(snapshot)
    if metadata.kind != SNAPSHOT_KIND:
        raise SnapshotRestoreError(f"Unsupported snapshot kind {metadata.kind!r}.")
    if metadata.schema_version > SNAPSHOT_SCHEMA_VERSION:
        raise SnapshotRestoreError(
            f"Unsupported snapshot schema version {metadata.schema_version}."
        )

    restore_catalog = catalog or SnapshotRestoreCatalog()
    agent_snapshot = _require_dict(snapshot.get("agent"), "agent")
    agent_name = _require_str(agent_snapshot.get("name"), "agent.name")
    tools = _restore_agent_tools(agent_snapshot, restore_catalog)
    memory = restore_catalog.memory or _restore_memory(agent_snapshot.get("memory"))
    agent = Agent(
        name=agent_name,
        instructions=restore_catalog.instructions,
        provider=restore_catalog.provider or MockProvider(),
        tools=tools,
        memory=memory,
    )
    session = Session(agent=agent)
    session.dialogue = _restore_dialogue(snapshot.get("dialogue"))
    session.events = _restore_events(snapshot.get("events"))
    session.checkpoints = _restore_checkpoints(snapshot.get("checkpoints"))
    session.pending_tool_calls = _restore_pending_tool_calls(
        snapshot.get("pending_tool_calls"),
        restore_catalog,
    )
    session.pending_workflows = _restore_pending_workflows(
        snapshot.get("pending_workflows"),
        restore_catalog,
        PendingWorkflow,
    )
    session.events.emit(EventType.SESSION_RESTORED, checkpoints=len(session.checkpoints))
    return session


def _restore_events(value: Any) -> EventLog:
    events = EventLog()
    if value is None:
        return events
    if not isinstance(value, list):
        raise SnapshotRestoreError("events must be a list.")
    for index, item in enumerate(value):
        event = _require_dict(item, f"events.{index}")
        created_at = event.get("created_at")
        try:
            parsed_created_at = (
                datetime.fromisoformat(created_at)
                if isinstance(created_at, str)
                else datetime.now().astimezone()
            )
        except ValueError as exc:
            raise SnapshotRestoreError(f"Event {index} has invalid created_at.") from exc
        try:
            schema_version = int(event.get("schema_version") or 1)
        except (TypeError, ValueError) as exc:
            raise SnapshotRestoreError(f"Event {index} has invalid schema_version.") from exc
        events.append(
            Event(
                type=_require_str(event.get("type"), f"events.{index}.type"),
                payload=_optional_dict(event.get("payload")),
                id=_require_str(event.get("id"), f"events.{index}.id"),
                created_at=parsed_created_at,
                schema_version=schema_version,
            )
        )
    return events


def _restore_agent_tools(
    agent_snapshot: dict[str, Any],
    catalog: SnapshotRestoreCatalog,
) -> list[Tool]:
    manifests = agent_snapshot.get("tools") or []
    tools: list[Tool] = []
    for manifest in manifests:
        if not isinstance(manifest, dict):
            continue
        name = manifest.get("name")
        if not isinstance(name, str):
            continue
        tool = catalog.tools.get(name)
        if tool is None:
            raise SnapshotRestoreError(f"Snapshot requires tool {name!r}.")
        tools.append(tool)
    return tools


def _restore_pending_tool_calls(
    value: Any,
    catalog: SnapshotRestoreCatalog,
) -> dict[str, ToolCall]:
    calls: dict[str, ToolCall] = {}
    if value is None:
        return calls
    if not isinstance(value, dict):
        raise SnapshotRestoreError("pending_tool_calls must be an object.")
    for checkpoint_id, item in value.items():
        call = _require_dict(item, f"pending_tool_calls.{checkpoint_id}")
        name = _require_str(call.get("name"), f"pending_tool_calls.{checkpoint_id}.name")
        if name not in catalog.tools:
            raise SnapshotRestoreError(f"Snapshot requires pending tool {name!r}.")
        args = call.get("args") or []
        kwargs = call.get("kwargs") or {}
        if not isinstance(args, list) or not isinstance(kwargs, dict):
            raise SnapshotRestoreError(f"Pending tool call {checkpoint_id!r} is invalid.")
        calls[str(checkpoint_id)] = ToolCall(
            name=name,
            args=tuple(args),
            kwargs=dict(kwargs),
            risk=call.get("risk", "low"),
            action=call.get("action", "tool_call"),
        )
    return calls


def _restore_pending_workflows(
    value: Any,
    catalog: SnapshotRestoreCatalog,
    pending_workflow_cls,
) -> dict[str, Any]:
    pending: dict[str, Any] = {}
    if value is None:
        return pending
    if not isinstance(value, dict):
        raise SnapshotRestoreError("pending_workflows must be an object.")
    for checkpoint_id, item in value.items():
        record = _require_dict(item, f"pending_workflows.{checkpoint_id}")
        workflow_name = _require_str(
            record.get("workflow"),
            f"pending_workflows.{checkpoint_id}.workflow",
        )
        workflow = catalog.workflows.get(workflow_name)
        if workflow is None:
            raise SnapshotRestoreError(f"Snapshot requires workflow {workflow_name!r}.")
        completed = record.get("completed_steps") or []
        if not isinstance(completed, list):
            raise SnapshotRestoreError(
                f"Pending workflow {checkpoint_id!r} completed_steps must be a list."
            )
        pending[str(checkpoint_id)] = pending_workflow_cls(
            workflow=workflow,
            state=record.get("state"),
            next_step=int(record.get("next_step") or 0),
            completed_steps=[str(step) for step in completed],
        )
    return pending


def _restore_checkpoints(value: Any) -> list[Checkpoint]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SnapshotRestoreError("checkpoints must be a list.")
    checkpoints: list[Checkpoint] = []
    for index, item in enumerate(value):
        checkpoint = _require_dict(item, f"checkpoints.{index}")
        checkpoints.append(
            Checkpoint(
                reason=_require_str(checkpoint.get("reason"), f"checkpoints.{index}.reason"),
                action=_require_str(checkpoint.get("action"), f"checkpoints.{index}.action"),
                payload=_optional_dict(checkpoint.get("payload")),
                summary=_optional_str(checkpoint.get("summary")),
                risk_reason=_optional_str(checkpoint.get("risk_reason")),
                preview=_optional_str(checkpoint.get("preview")),
                options=_restore_options(checkpoint.get("options")),
                id=_require_str(checkpoint.get("id"), f"checkpoints.{index}.id"),
                status=CheckpointStatus(checkpoint.get("status") or "pending"),
            )
        )
    return checkpoints


def _restore_dialogue(value: Any) -> Dialogue:
    if value is None:
        return Dialogue()
    data = _require_dict(value, "dialogue")
    dialogue = Dialogue(
        messages=[
            Message(
                role=_require_str(message.get("role"), "dialogue.messages.role"),
                content=_require_str(message.get("content"), "dialogue.messages.content"),
            )
            for message in data.get("messages", [])
            if isinstance(message, dict)
        ],
        user_goal=_optional_str(data.get("user_goal")),
        goal=_restore_goal(data.get("goal")),
        intent=_restore_intent(data.get("intent")),
        constraints=[str(item) for item in data.get("constraints", [])],
        preferences={str(key): str(item) for key, item in data.get("preferences", {}).items()},
        clarifications=_restore_clarifications(data.get("clarifications")),
        open_questions=[str(item) for item in data.get("open_questions", [])],
        confirmations=[str(item) for item in data.get("confirmations", [])],
    )
    return dialogue


def _restore_memory(value: Any) -> SessionMemory:
    if not isinstance(value, dict):
        return SessionMemory()
    preferences = UserPreferences(dict(_optional_dict(value.get("preferences"))))
    project_data = _optional_dict(value.get("project"))
    project = ProjectContext(
        name=_optional_str(project_data.get("name")),
        description=_optional_str(project_data.get("description")),
        metadata=_optional_dict(project_data.get("metadata")),
    )
    return SessionMemory(
        preferences=preferences,
        project=project,
        scratchpad=_optional_dict(value.get("scratchpad")),
    )


def _restore_goal(value: Any) -> UserGoal | None:
    if value is None:
        return None
    data = _require_dict(value, "dialogue.goal")
    return UserGoal(
        text=_require_str(data.get("text"), "dialogue.goal.text"),
        constraints=[str(item) for item in data.get("constraints", [])],
        preferences={str(key): str(item) for key, item in data.get("preferences", {}).items()},
    )


def _restore_intent(value: Any) -> Intent | None:
    if value is None:
        return None
    data = _require_dict(value, "dialogue.intent")
    return Intent(
        type=IntentType(_require_str(data.get("type"), "dialogue.intent.type")),
        summary=_require_str(data.get("summary"), "dialogue.intent.summary"),
        confidence=float(data.get("confidence", 1.0)),
        needs_clarification=bool(data.get("needs_clarification", False)),
    )


def _restore_clarifications(value: Any) -> list[Clarification]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SnapshotRestoreError("dialogue.clarifications must be a list.")
    return [
        Clarification(
            question=_require_str(item.get("question"), "dialogue.clarifications.question"),
            reason=_require_str(item.get("reason"), "dialogue.clarifications.reason"),
        )
        for item in value
        if isinstance(item, dict)
    ]


def _restore_options(value: Any) -> list[str]:
    if value is None:
        return ["approve", "reject"]
    if not isinstance(value, list):
        raise SnapshotRestoreError("checkpoint options must be a list.")
    return [str(item) for item in value]


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SnapshotRestoreError(f"Snapshot field {name} must be an object.")
    return value


def _optional_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _require_str(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise SnapshotRestoreError(f"Snapshot field {name} must be a string.")
    return value


def _optional_str(value: Any) -> str | None:
    if value is None or isinstance(value, str):
        return value
    return str(value)
