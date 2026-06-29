"""Helpers for JSON-safe snapshots."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any

DEFAULT_REDACT_KEYS = {
    "api_key",
    "authorization",
    "bearer",
    "content",
    "password",
    "secret",
    "token",
}


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


def redact_jsonable(
    value: Any,
    *,
    redact_keys: set[str] | None = None,
    replacement: str = "[REDACTED]",
) -> Any:
    """Redact sensitive fields from a JSON-safe value."""

    keys = redact_keys or DEFAULT_REDACT_KEYS

    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            lowered = key_text.lower()
            if any(sensitive in lowered for sensitive in keys):
                redacted[key_text] = replacement
            else:
                redacted[key_text] = redact_jsonable(
                    item,
                    redact_keys=keys,
                    replacement=replacement,
                )
        return redacted

    if isinstance(value, list):
        return [
            redact_jsonable(item, redact_keys=keys, replacement=replacement)
            for item in value
        ]

    return value
