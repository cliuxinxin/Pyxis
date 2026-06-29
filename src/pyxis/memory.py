"""Memory primitives."""

from __future__ import annotations

from typing import Any, Protocol


class Memory(Protocol):
    """Minimal key-value memory interface."""

    def get(self, key: str, default: Any = None) -> Any:
        ...

    def set(self, key: str, value: Any) -> None:
        ...


class NoMemory:
    """Memory implementation that intentionally stores nothing."""

    def get(self, key: str, default: Any = None) -> Any:
        return default

    def set(self, key: str, value: Any) -> None:
        return None


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
