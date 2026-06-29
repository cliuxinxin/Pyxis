"""Control policies for human-in-the-loop workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from pyxis.types import RiskLevel


class ApprovalMode(str, Enum):
    """How aggressively Pyxis should ask for human approval."""

    PERMISSIVE = "permissive"
    BALANCED = "balanced"
    STRICT = "strict"


@dataclass(frozen=True)
class PolicyDecision:
    """A control-policy decision for one action."""

    allowed: bool
    requires_confirmation: bool
    reason: str
    action: str
    risk: RiskLevel
    effective_risk: RiskLevel
    options: list[str] = field(default_factory=lambda: ["approve", "reject"])


@dataclass(frozen=True)
class ControlPolicy:
    """Rules that decide which actions need explicit confirmation."""

    approval_mode: ApprovalMode | str = ApprovalMode.BALANCED
    require_confirmation_for_risk: set[RiskLevel] = field(default_factory=lambda: {"high"})
    require_confirmation_for_actions: set[str] = field(default_factory=set)
    allow_auto_for_actions: set[str] = field(default_factory=set)
    deny_actions: set[str] = field(default_factory=set)
    risk_overrides: dict[str, RiskLevel] = field(default_factory=dict)
    checkpoint_options: list[str] = field(default_factory=lambda: ["approve", "reject"])

    @classmethod
    def safe_default(cls) -> ControlPolicy:
        return cls(
            approval_mode=ApprovalMode.BALANCED,
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

    @classmethod
    def strict(cls) -> ControlPolicy:
        return cls(approval_mode=ApprovalMode.STRICT)

    @classmethod
    def permissive(cls) -> ControlPolicy:
        return cls(
            approval_mode=ApprovalMode.PERMISSIVE,
            require_confirmation_for_risk=set(),
            require_confirmation_for_actions=set(),
        )

    def decide(self, *, action: str, risk: RiskLevel = "low") -> PolicyDecision:
        effective_risk = self.risk_overrides.get(action, risk)
        options = list(self.checkpoint_options)
        mode = ApprovalMode(self.approval_mode)

        if action in self.deny_actions:
            return PolicyDecision(
                allowed=False,
                requires_confirmation=False,
                reason=f"Action {action!r} is denied by policy.",
                action=action,
                risk=risk,
                effective_risk=effective_risk,
                options=options,
            )

        if action in self.allow_auto_for_actions:
            return PolicyDecision(
                allowed=True,
                requires_confirmation=False,
                reason=f"Action {action!r} is allowed to run automatically.",
                action=action,
                risk=risk,
                effective_risk=effective_risk,
                options=options,
            )

        if mode == ApprovalMode.STRICT:
            return PolicyDecision(
                allowed=True,
                requires_confirmation=True,
                reason="Strict approval mode requires confirmation.",
                action=action,
                risk=risk,
                effective_risk=effective_risk,
                options=options,
            )

        requires_confirmation = (
            action in self.require_confirmation_for_actions
            or effective_risk in self.require_confirmation_for_risk
        )
        if requires_confirmation:
            return PolicyDecision(
                allowed=True,
                requires_confirmation=True,
                reason=(
                    f"Action {action!r} requires confirmation "
                    f"with effective risk {effective_risk!r}."
                ),
                action=action,
                risk=risk,
                effective_risk=effective_risk,
                options=options,
            )

        return PolicyDecision(
            allowed=True,
            requires_confirmation=False,
            reason=f"Action {action!r} may run automatically.",
            action=action,
            risk=risk,
            effective_risk=effective_risk,
            options=options,
        )

    def requires_confirmation(self, *, action: str, risk: RiskLevel = "low") -> bool:
        return self.decide(action=action, risk=risk).requires_confirmation
