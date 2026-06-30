"""Memory primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from pyxis.serialization import to_jsonable


class Memory(Protocol):
    """Minimal key-value memory interface."""

    def get(self, key: str, default: Any = None) -> Any:
        ...

    def set(self, key: str, value: Any) -> None:
        ...

    def to_dict(self) -> dict[str, Any]:
        ...


class NoMemory:
    """Memory implementation that intentionally stores nothing."""

    def get(self, key: str, default: Any = None) -> Any:
        return default

    def set(self, key: str, value: Any) -> None:
        return None

    def to_dict(self) -> dict[str, Any]:
        return {}


@dataclass(frozen=True)
class MemoryItem:
    """A namespaced long-term memory item."""

    namespace: str
    key: str
    value: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "key": self.key,
            "value": to_jsonable(self.value),
            "metadata": to_jsonable(self.metadata),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MemoryStore(Protocol):
    """Protocol for long-term, namespaced memory adapters."""

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        ...

    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        ...

    def delete(self, namespace: str, key: str) -> None:
        ...

    def list(self, namespace: str) -> list[MemoryItem]:
        ...

    def to_dict(self) -> dict[str, Any]:
        ...


class NoMemoryStore:
    """Memory store implementation that intentionally stores nothing."""

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        return default

    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        return None

    def delete(self, namespace: str, key: str) -> None:
        return None

    def list(self, namespace: str) -> list[MemoryItem]:
        return []

    def to_dict(self) -> dict[str, Any]:
        return {"items": [], "persistent": False}


class InMemoryStore:
    """In-process namespaced memory store for tests and local applications."""

    def __init__(self, items: list[MemoryItem] | None = None) -> None:
        self._items: dict[tuple[str, str], MemoryItem] = {}
        for item in items or []:
            self._items[(item.namespace, item.key)] = item

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        item = self._items.get((namespace, key))
        if item is None:
            return default
        return item.value

    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        existing = self._items.get((namespace, key))
        created_at = existing.created_at if existing else datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc) if existing else None
        self._items[(namespace, key)] = MemoryItem(
            namespace=namespace,
            key=key,
            value=value,
            metadata=dict(metadata or {}),
            created_at=created_at,
            updated_at=updated_at,
        )

    def delete(self, namespace: str, key: str) -> None:
        self._items.pop((namespace, key), None)

    def list(self, namespace: str) -> list[MemoryItem]:
        return [
            item
            for item in self._items.values()
            if item.namespace == namespace
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self._items.values()],
            "persistent": False,
        }


class InMemory:
    """Simple in-process memory for sessions and tests."""

    def __init__(self, initial: dict[str, Any] | None = None) -> None:
        self._data = dict(initial or {})

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def as_dict(self) -> dict[str, Any]:
        return dict(self._data)

    def to_dict(self) -> dict[str, Any]:
        return self.as_dict()


@dataclass
class UserPreferences:
    """Explicit, inspectable user preferences."""

    values: dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any) -> None:
        self.values[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def clear(self, key: str | None = None) -> None:
        if key is None:
            self.values.clear()
            return
        self.values.pop(key, None)

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self.values)


@dataclass
class ProjectContext:
    """Bounded project context chosen by the embedding application."""

    name: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def set(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if metadata is not None:
            self.metadata.update(metadata)

    def clear(self) -> None:
        self.name = None
        self.description = None
        self.metadata.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "metadata": to_jsonable(self.metadata),
        }


class SessionMemory:
    """Bounded in-process memory with explicit user controls."""

    def __init__(
        self,
        *,
        preferences: UserPreferences | None = None,
        project: ProjectContext | None = None,
        scratchpad: dict[str, Any] | None = None,
        store: MemoryStore | None = None,
    ) -> None:
        self.preferences = preferences or UserPreferences()
        self.project = project or ProjectContext()
        self._scratchpad = dict(scratchpad or {})
        self.store = store

    def get(self, key: str, default: Any = None) -> Any:
        return self._scratchpad.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._scratchpad[key] = value

    def clear(self, key: str | None = None) -> None:
        if key is None:
            self._scratchpad.clear()
            return
        self._scratchpad.pop(key, None)

    def set_preference(self, key: str, value: Any) -> None:
        self.preferences.set(key, value)

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self.preferences.get(key, default)

    def clear_preferences(self, key: str | None = None) -> None:
        self.preferences.clear(key)

    def set_project_context(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.project.set(name=name, description=description, metadata=metadata)

    def clear_project_context(self) -> None:
        self.project.clear()

    def as_dict(self) -> dict[str, Any]:
        return self.to_dict()

    def to_dict(self) -> dict[str, Any]:
        data = {
            "preferences": self.preferences.to_dict(),
            "project": self.project.to_dict(),
            "scratchpad": to_jsonable(self._scratchpad),
            "persistent": False,
        }
        if self.store is not None:
            data["store"] = to_jsonable(self.store.to_dict())
        return data
