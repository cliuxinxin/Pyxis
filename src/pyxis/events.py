"""Event recording for observable agent sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pyxis.serialization import to_jsonable

EVENT_SCHEMA_VERSION = 1


class EventType(str, Enum):
    """Stable event names emitted by Pyxis sessions."""

    USER_MESSAGE_RECEIVED = "UserMessageReceived"
    COMPASS_DECISION_MADE = "CompassDecisionMade"
    AGENT_ACTION_PARSED = "AgentActionParsed"
    AGENT_RESPONDED = "AgentResponded"
    PROVIDER_STARTED = "ProviderStarted"
    PROVIDER_DONE = "ProviderDone"
    PROVIDER_ERROR = "ProviderError"
    CHECKPOINT_CREATED = "CheckpointCreated"
    CHECKPOINT_APPROVED = "CheckpointApproved"
    CHECKPOINT_REJECTED = "CheckpointRejected"
    CHECKPOINT_RESUMED = "CheckpointResumed"
    TOOL_VALIDATION_FAILED = "ToolValidationFailed"
    TOOL_CALL_REQUESTED = "ToolCallRequested"
    TOOL_CALL_PAUSED = "ToolCallPaused"
    TOOL_CALL_COMPLETED = "ToolCallCompleted"
    POLICY_DENIED = "PolicyDenied"
    WORKFLOW_STARTED = "WorkflowStarted"
    WORKFLOW_STEP_STARTED = "WorkflowStepStarted"
    WORKFLOW_STEP_COMPLETED = "WorkflowStepCompleted"
    WORKFLOW_STEP_FAILED = "WorkflowStepFailed"
    WORKFLOW_PAUSED = "WorkflowPaused"
    WORKFLOW_RESUMED = "WorkflowResumed"
    WORKFLOW_COMPLETED = "WorkflowCompleted"
    SESSION_RESTORED = "SessionRestored"


@dataclass(frozen=True)
class EventSchema:
    """Payload contract for a stable Pyxis event."""

    type: str
    required: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()
    description: str = ""


EVENT_SCHEMAS: dict[str, EventSchema] = {
    EventType.USER_MESSAGE_RECEIVED.value: EventSchema(
        type=EventType.USER_MESSAGE_RECEIVED.value,
        required=("content",),
        description="A user message was accepted into the session.",
    ),
    EventType.COMPASS_DECISION_MADE.value: EventSchema(
        type=EventType.COMPASS_DECISION_MADE.value,
        required=("decision", "reason", "intent", "needs_clarification"),
        description="The dialogue compass classified the next navigation step.",
    ),
    EventType.AGENT_ACTION_PARSED.value: EventSchema(
        type=EventType.AGENT_ACTION_PARSED.value,
        required=("action",),
        description="A model response was parsed for a structured agent action.",
    ),
    EventType.AGENT_RESPONDED.value: EventSchema(
        type=EventType.AGENT_RESPONDED.value,
        required=("content",),
        description="The agent produced user-facing output.",
    ),
    EventType.PROVIDER_STARTED.value: EventSchema(
        type=EventType.PROVIDER_STARTED.value,
        required=("agent", "provider", "mode"),
        description="A provider completion or stream request started.",
    ),
    EventType.PROVIDER_DONE.value: EventSchema(
        type=EventType.PROVIDER_DONE.value,
        required=("agent", "provider", "mode"),
        optional=("finish_reason", "usage", "chunks"),
        description="A provider completion or stream request finished.",
    ),
    EventType.PROVIDER_ERROR.value: EventSchema(
        type=EventType.PROVIDER_ERROR.value,
        required=("agent", "provider", "mode", "error", "message"),
        description="A provider completion or stream request failed.",
    ),
    EventType.CHECKPOINT_CREATED.value: EventSchema(
        type=EventType.CHECKPOINT_CREATED.value,
        required=("checkpoint_id", "reason", "action"),
        description="A human approval checkpoint was created.",
    ),
    EventType.CHECKPOINT_APPROVED.value: EventSchema(
        type=EventType.CHECKPOINT_APPROVED.value,
        required=("checkpoint_id",),
        description="A checkpoint was approved.",
    ),
    EventType.CHECKPOINT_REJECTED.value: EventSchema(
        type=EventType.CHECKPOINT_REJECTED.value,
        required=("checkpoint_id",),
        description="A checkpoint was rejected.",
    ),
    EventType.CHECKPOINT_RESUMED.value: EventSchema(
        type=EventType.CHECKPOINT_RESUMED.value,
        required=("checkpoint_id",),
        optional=("tool",),
        description="A checkpointed action resumed after approval.",
    ),
    EventType.TOOL_VALIDATION_FAILED.value: EventSchema(
        type=EventType.TOOL_VALIDATION_FAILED.value,
        required=("tool", "error"),
        description="A tool call failed argument validation before execution.",
    ),
    EventType.TOOL_CALL_REQUESTED.value: EventSchema(
        type=EventType.TOOL_CALL_REQUESTED.value,
        required=("tool", "action", "risk"),
        description="A tool call was requested.",
    ),
    EventType.TOOL_CALL_PAUSED.value: EventSchema(
        type=EventType.TOOL_CALL_PAUSED.value,
        required=("tool", "checkpoint_id"),
        optional=("policy_reason",),
        description="A tool call paused for human confirmation.",
    ),
    EventType.TOOL_CALL_COMPLETED.value: EventSchema(
        type=EventType.TOOL_CALL_COMPLETED.value,
        required=("tool",),
        optional=("checkpoint_id",),
        description="A tool call completed.",
    ),
    EventType.POLICY_DENIED.value: EventSchema(
        type=EventType.POLICY_DENIED.value,
        required=("tool", "action", "reason"),
        description="A policy denied an action before execution.",
    ),
    EventType.WORKFLOW_STARTED.value: EventSchema(
        type=EventType.WORKFLOW_STARTED.value,
        required=("workflow",),
        description="A workflow run started.",
    ),
    EventType.WORKFLOW_STEP_STARTED.value: EventSchema(
        type=EventType.WORKFLOW_STEP_STARTED.value,
        required=("workflow", "step", "index", "kind"),
        description="A workflow step started.",
    ),
    EventType.WORKFLOW_STEP_COMPLETED.value: EventSchema(
        type=EventType.WORKFLOW_STEP_COMPLETED.value,
        required=("workflow", "step", "index", "kind"),
        description="A workflow step completed.",
    ),
    EventType.WORKFLOW_STEP_FAILED.value: EventSchema(
        type=EventType.WORKFLOW_STEP_FAILED.value,
        required=("workflow", "step", "index", "kind", "error", "message"),
        description="A workflow step raised an exception.",
    ),
    EventType.WORKFLOW_PAUSED.value: EventSchema(
        type=EventType.WORKFLOW_PAUSED.value,
        required=("workflow", "checkpoint_id"),
        description="A workflow paused at a checkpoint.",
    ),
    EventType.WORKFLOW_RESUMED.value: EventSchema(
        type=EventType.WORKFLOW_RESUMED.value,
        required=("workflow", "checkpoint_id"),
        description="A workflow resumed after checkpoint approval.",
    ),
    EventType.WORKFLOW_COMPLETED.value: EventSchema(
        type=EventType.WORKFLOW_COMPLETED.value,
        required=("workflow", "steps"),
        description="A workflow completed.",
    ),
    EventType.SESSION_RESTORED.value: EventSchema(
        type=EventType.SESSION_RESTORED.value,
        required=("checkpoints",),
        description="A session was restored from a snapshot.",
    ),
}


@dataclass(frozen=True)
class Event:
    """A timestamped event emitted by a Pyxis session."""

    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: int = EVENT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "payload": to_jsonable(self.payload),
            "created_at": self.created_at.isoformat(),
            "schema_version": self.schema_version,
        }


class EventLog:
    """Append-only event log."""

    def __init__(self) -> None:
        self._events: list[Event] = []

    def emit(self, event_type: str | EventType, **payload: Any) -> Event:
        event_name = event_type.value if isinstance(event_type, EventType) else event_type
        self._validate_payload(event_name, payload)
        event = Event(type=event_name, payload=payload)
        self._events.append(event)
        return event

    def append(self, event: Event) -> None:
        self._events.append(event)

    def all(self) -> list[Event]:
        return list(self._events)

    def to_list(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self._events]

    def __iter__(self):
        return iter(self._events)

    def __len__(self) -> int:
        return len(self._events)

    def _validate_payload(self, event_type: str, payload: dict[str, Any]) -> None:
        schema = EVENT_SCHEMAS.get(event_type)
        if schema is None:
            return
        missing = [key for key in schema.required if key not in payload]
        if missing:
            formatted = ", ".join(missing)
            raise ValueError(f"Event {event_type!r} is missing required payload: {formatted}.")
