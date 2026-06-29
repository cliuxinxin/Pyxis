"""Snapshot persistence helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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
