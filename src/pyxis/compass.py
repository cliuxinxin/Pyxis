"""Navigation decisions for human-centered agent sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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


class Compass:
    """Decides whether to ask, plan, act, confirm, or stop."""

    ambiguous_markers = ("something", "stuff", "whatever", "帮我弄一下", "随便")
    plan_markers = ("plan", "设计", "规划", "计划", "workflow", "流程")
    stop_markers = ("stop", "cancel", "停止", "取消")

    def decide(self, user_input: str, *, requires_confirmation: bool = False) -> CompassDecision:
        normalized = user_input.strip().lower()

        if not normalized:
            return CompassDecision(
                type=CompassDecisionType.ASK_CLARIFICATION,
                reason="The user input is empty.",
                prompt="What would you like to work on?",
            )

        if any(marker in normalized for marker in self.stop_markers):
            return CompassDecision(
                type=CompassDecisionType.STOP,
                reason="The user asked to stop.",
            )

        if requires_confirmation:
            return CompassDecision(
                type=CompassDecisionType.REQUEST_CONFIRMATION,
                reason="The next action requires explicit confirmation.",
            )

        if any(marker in normalized for marker in self.ambiguous_markers):
            return CompassDecision(
                type=CompassDecisionType.ASK_CLARIFICATION,
                reason="The goal appears underspecified.",
                prompt="Can you clarify the outcome you want?",
            )

        if any(marker in normalized for marker in self.plan_markers):
            return CompassDecision(
                type=CompassDecisionType.PROPOSE_PLAN,
                reason="The user is asking for direction before execution.",
            )

        return CompassDecision(
            type=CompassDecisionType.RUN_AGENT,
            reason="The input is specific enough for the agent to answer.",
        )
