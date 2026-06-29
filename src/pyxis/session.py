"""Session orchestration for Pyxis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pyxis.agent import Agent
from pyxis.checkpoint import Checkpoint
from pyxis.compass import Compass, CompassDecisionType
from pyxis.dialogue import Dialogue
from pyxis.events import EventLog
from pyxis.policy import ControlPolicy
from pyxis.results import NavigationResult, WorkflowResult
from pyxis.workflow import Workflow


@dataclass
class Session:
    """A human-agent working context."""

    agent: Agent
    compass: Compass = field(default_factory=Compass)
    policy: ControlPolicy = field(default_factory=ControlPolicy.safe_default)
    dialogue: Dialogue = field(default_factory=Dialogue)
    events: EventLog = field(default_factory=EventLog)
    checkpoints: list[Checkpoint] = field(default_factory=list)

    def navigate(self, user_input: str, *, requires_confirmation: bool = False) -> NavigationResult:
        self.dialogue.add("user", user_input)
        self.events.emit("UserMessageReceived", content=user_input)

        decision = self.compass.decide(user_input, requires_confirmation=requires_confirmation)
        self.events.emit(
            "CompassDecisionMade",
            decision=decision.type.value,
            reason=decision.reason,
        )

        if decision.type == CompassDecisionType.ASK_CLARIFICATION:
            output = decision.prompt or "Can you clarify what you want to do next?"
        elif decision.type == CompassDecisionType.STOP:
            output = "Stopped."
        elif decision.type == CompassDecisionType.REQUEST_CONFIRMATION:
            checkpoint = self.checkpoint(
                reason=decision.reason,
                action="navigation",
                payload={"input": user_input},
            )
            output = f"Confirmation required before continuing: {checkpoint.reason}"
        elif decision.type == CompassDecisionType.PROPOSE_PLAN:
            result = self.agent.run(
                f"Propose a concise, controllable plan for this request:\n{user_input}",
                context={"decision": decision.type.value},
            )
            output = result.output
        else:
            result = self.agent.run(user_input, context={"decision": decision.type.value})
            output = result.output

        self.dialogue.add("agent", output)
        self.events.emit("AgentResponded", content=output)
        return NavigationResult(output=output, decision=decision.type.value)

    def checkpoint(
        self,
        *,
        reason: str,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> Checkpoint:
        checkpoint = Checkpoint(reason=reason, action=action, payload=payload or {})
        self.checkpoints.append(checkpoint)
        self.events.emit(
            "CheckpointCreated",
            checkpoint_id=checkpoint.id,
            reason=reason,
            action=action,
        )
        return checkpoint

    def run(self, workflow: Workflow, value: Any) -> WorkflowResult:
        self.events.emit("WorkflowStarted", workflow=workflow.name)
        result = workflow.run(value)
        self.events.emit("WorkflowCompleted", workflow=workflow.name, steps=result.steps)
        return result
