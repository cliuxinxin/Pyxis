"""Shared types used across Pyxis."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Literal, TypeAlias

RiskLevel: TypeAlias = Literal["low", "medium", "high"]
JsonDict: TypeAlias = dict[str, Any]
Metadata: TypeAlias = Mapping[str, Any]
CallableStep: TypeAlias = Callable[[Any], Any]
