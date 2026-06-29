"""Navigation decisions for human-centered agent sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pyxis.dialogue import Clarification, Intent, IntentType, UserGoal


class CompassDecisionType(str, Enum):
    """Possible next moves for a Pyxis session."""

    ASK_CLARIFICATION = "ask_clarification"
    PROPOSE_PLAN = "propose_plan"
    RUN_AGENT = "run_agent"
    REQUEST_CONFIRMATION = "request_confirmation"
    STOP = "stop"


@dataclass(frozen=True)
class CompassDecision:
    """A navigational decision for one turn."""

    type: CompassDecisionType
    reason: str
    prompt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CompassAnalysis:
    """A structured reading of a user turn and the next best move."""

    intent: Intent
    decision: CompassDecision
    goal: UserGoal | None = None
    clarification: Clarification | None = None
    constraints: list[str] = field(default_factory=list)
    preferences: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "intent": self.intent.to_dict(),
            "decision": {
                "type": self.decision.type.value,
                "reason": self.decision.reason,
                "prompt": self.decision.prompt,
                "metadata": dict(self.decision.metadata),
            },
            "goal": self.goal.to_dict() if self.goal else None,
            "clarification": self.clarification.to_dict() if self.clarification else None,
            "constraints": list(self.constraints),
            "preferences": dict(self.preferences),
        }


class Compass:
    """Decides whether to ask, plan, act, confirm, or stop."""

    ambiguous_markers = (
        "something",
        "stuff",
        "whatever",
        "帮我弄一下",
        "随便",
        "看看",
        "优化一下",
        "弄一下",
    )
    plan_markers = ("plan", "设计", "规划", "计划", "workflow", "流程")
    stop_markers = ("stop", "cancel", "停止", "取消")
    preference_markers = {
        "简洁": ("tone", "concise"),
        "详细": ("verbosity", "detailed"),
        "严格": ("approval_mode", "strict"),
        "保守": ("approval_mode", "strict"),
        "concise": ("tone", "concise"),
        "detailed": ("verbosity", "detailed"),
        "strict": ("approval_mode", "strict"),
    }
    constraint_markers = ("必须", "不要", "不能", "需要", "must", "without", "avoid")

    def decide(self, user_input: str, *, requires_confirmation: bool = False) -> CompassDecision:
        return self.analyze(
            user_input,
            requires_confirmation=requires_confirmation,
        ).decision

    def analyze(
        self,
        user_input: str,
        *,
        requires_confirmation: bool = False,
    ) -> CompassAnalysis:
        """Read a user turn into intent, goal, constraints, and next move."""

        normalized = user_input.strip().lower()
        text = user_input.strip()
        constraints = self._extract_constraints(text)
        preferences = self._extract_preferences(normalized)

        if not normalized:
            intent = Intent(
                type=IntentType.UNKNOWN,
                summary="The user has not provided a request yet.",
                confidence=0.0,
                needs_clarification=True,
            )
            clarification = Clarification(
                question="What would you like to work on?",
                reason="The user input is empty.",
            )
            decision = CompassDecision(
                type=CompassDecisionType.ASK_CLARIFICATION,
                reason="The user input is empty.",
                prompt=clarification.question,
            )
            return CompassAnalysis(
                intent=intent,
                decision=decision,
                clarification=clarification,
            )

        if any(marker in normalized for marker in self.stop_markers):
            intent = Intent(
                type=IntentType.STOP,
                summary="The user wants to stop the current work.",
            )
            decision = CompassDecision(
                type=CompassDecisionType.STOP,
                reason="The user asked to stop.",
            )
            return CompassAnalysis(
                intent=intent,
                decision=decision,
                goal=UserGoal(text=text, constraints=constraints, preferences=preferences),
                constraints=constraints,
                preferences=preferences,
            )

        if requires_confirmation:
            intent = Intent(
                type=IntentType.CONFIRM,
                summary="The user request is ready to continue but needs confirmation.",
            )
            decision = CompassDecision(
                type=CompassDecisionType.REQUEST_CONFIRMATION,
                reason="The next action requires explicit confirmation.",
            )
            return CompassAnalysis(
                intent=intent,
                decision=decision,
                goal=UserGoal(text=text, constraints=constraints, preferences=preferences),
                constraints=constraints,
                preferences=preferences,
            )

        if self._needs_clarification(normalized):
            intent = Intent(
                type=IntentType.UNKNOWN,
                summary="The user wants help but the desired outcome is underspecified.",
                confidence=0.45,
                needs_clarification=True,
            )
            clarification = Clarification(
                question="Can you clarify the outcome you want?",
                reason="The goal appears underspecified.",
            )
            decision = CompassDecision(
                type=CompassDecisionType.ASK_CLARIFICATION,
                reason="The goal appears underspecified.",
                prompt=clarification.question,
            )
            return CompassAnalysis(
                intent=intent,
                decision=decision,
                clarification=clarification,
                constraints=constraints,
                preferences=preferences,
            )

        if any(marker in normalized for marker in self.plan_markers):
            intent = Intent(
                type=IntentType.PLAN,
                summary="The user is asking for a plan or direction before execution.",
            )
            decision = CompassDecision(
                type=CompassDecisionType.PROPOSE_PLAN,
                reason="The user is asking for direction before execution.",
            )
            return CompassAnalysis(
                intent=intent,
                decision=decision,
                goal=UserGoal(text=text, constraints=constraints, preferences=preferences),
                constraints=constraints,
                preferences=preferences,
            )

        intent = Intent(
            type=IntentType.ACT,
            summary="The user request is specific enough for an agent response.",
        )
        decision = CompassDecision(
            type=CompassDecisionType.RUN_AGENT,
            reason="The input is specific enough for the agent to answer.",
        )
        return CompassAnalysis(
            intent=intent,
            decision=decision,
            goal=UserGoal(text=text, constraints=constraints, preferences=preferences),
            constraints=constraints,
            preferences=preferences,
        )

    def _needs_clarification(self, normalized: str) -> bool:
        if any(marker in normalized for marker in self.ambiguous_markers):
            return True
        return len(normalized) <= 2

    def _extract_constraints(self, text: str) -> list[str]:
        constraints: list[str] = []
        for marker in self.constraint_markers:
            if marker in text:
                constraints.append(text)
                break
        return constraints

    def _extract_preferences(self, normalized: str) -> dict[str, str]:
        preferences: dict[str, str] = {}
        for marker, (key, value) in self.preference_markers.items():
            if marker in normalized:
                preferences[key] = value
        return preferences
