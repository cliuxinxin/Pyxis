"""Control policies for human-in-the-loop workflows."""

from __future__ import annotations

from dataclasses import dataclass, field

from pyxis.types import RiskLevel


@dataclass(frozen=True)
class ControlPolicy:
    """Rules that decide which actions need explicit confirmation."""

    require_confirmation_for_risk: set[RiskLevel] = field(default_factory=lambda: {"high"})
    require_confirmation_for_actions: set[str] = field(default_factory=set)
    allow_auto_for_actions: set[str] = field(default_factory=set)

    @classmethod
    def safe_default(cls) -> ControlPolicy:
        return cls(
            require_confirmation_for_risk={"high"},
            require_confirmation_for_actions={
                "email_send",
                "file_write",
                "network_post",
                "payment",
                "shell_exec",
            },
            allow_auto_for_actions={
                "classify",
                "draft",
                "summarize",
            },
        )

    def requires_confirmation(self, *, action: str, risk: RiskLevel = "low") -> bool:
        if action in self.allow_auto_for_actions:
            return False
        return (
            action in self.require_confirmation_for_actions
            or risk in self.require_confirmation_for_risk
        )
