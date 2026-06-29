"""Memory primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
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
    ) -> None:
        self.preferences = preferences or UserPreferences()
        self.project = project or ProjectContext()
        self._scratchpad = dict(scratchpad or {})

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
        return {
            "preferences": self.preferences.to_dict(),
            "project": self.project.to_dict(),
            "scratchpad": to_jsonable(self._scratchpad),
            "persistent": False,
        }
