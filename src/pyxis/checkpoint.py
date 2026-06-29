"""Human confirmation checkpoints."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class CheckpointStatus(str, Enum):
    """Checkpoint lifecycle states."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class Checkpoint:
    """A point where human confirmation may be required."""

    reason: str
    action: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    status: CheckpointStatus = CheckpointStatus.PENDING

    def approve(self) -> None:
        self.status = CheckpointStatus.APPROVED

    def reject(self) -> None:
        self.status = CheckpointStatus.REJECTED

    @property
    def approved(self) -> bool:
        return self.status == CheckpointStatus.APPROVED
