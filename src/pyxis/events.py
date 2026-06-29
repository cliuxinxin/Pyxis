"""Event recording for observable agent sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pyxis.serialization import to_jsonable


@dataclass(frozen=True)
class Event:
    """A timestamped event emitted by a Pyxis session."""

    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "payload": to_jsonable(self.payload),
            "created_at": self.created_at.isoformat(),
        }


class EventLog:
    """Append-only event log."""

    def __init__(self) -> None:
        self._events: list[Event] = []

    def emit(self, event_type: str, **payload: Any) -> Event:
        event = Event(type=event_type, payload=payload)
        self._events.append(event)
        return event

    def all(self) -> list[Event]:
        return list(self._events)

    def to_list(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self._events]

    def __iter__(self):
        return iter(self._events)

    def __len__(self) -> int:
        return len(self._events)
