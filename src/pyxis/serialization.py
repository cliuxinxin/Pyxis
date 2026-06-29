"""Helpers for JSON-safe snapshots."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any


def to_jsonable(value: Any) -> Any:
    """Convert common Python objects into JSON-safe values."""

    if value is None or isinstance(value, str | int | float | bool):
        return value

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}

    if isinstance(value, tuple | list | set):
        return [to_jsonable(item) for item in value]

    if is_dataclass(value):
        return to_jsonable(asdict(value))

    return repr(value)
