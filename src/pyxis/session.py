"""Session orchestration for Pyxis."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pyxis.actions import AgentActionType, parse_agent_action
from pyxis.agent import Agent
from pyxis.checkpoint import Checkpoint, CheckpointStatus
from pyxis.compass import Compass, CompassDecisionType
from pyxis.dialogue import Dialogue
from pyxis.errors import CheckpointNotApproved, CheckpointNotFound, CheckpointRejected, ToolNotFound
from pyxis.events import EventLog
from pyxis.policy import ControlPolicy
from pyxis.results import NavigationResult, StreamEvent, ToolResult, WorkflowResult
from pyxis.serialization import to_jsonable
from pyxis.snapshots import save_snapshot
from pyxis.tools import ToolCall
from pyxis.workflow import Workflow


@dataclass(frozen=True)
class PendingWorkflow:
    """A workflow paused at a checkpoint."""

    workflow: Workflow
    state: Any
    next_step: int
    completed_steps: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow": self.workflow.name,
            "state": to_jsonable(self.state),
            "next_step": self.next_step,
            "completed_steps": list(self.completed_steps),
        }


@dataclass
class Session:
    """A human-agent working context."""

    agent: Agent
    compass: Compass = field(default_factory=Compass)
    policy: ControlPolicy = field(default_factory=ControlPolicy.safe_default)
    dialogue: Dialogue = field(default_factory=Dialogue)
    events: EventLog = field(default_factory=EventLog)
    checkpoints: list[Checkpoint] = field(default_factory=list)
    pending_tool_calls: dict[str, ToolCall] = field(default_factory=dict)
    pending_workflows: dict[str, PendingWorkflow] = field(default_factory=dict)

    def navigate(self, user_input: str, *, requires_confirmation: bool = False) -> NavigationResult:
        self.dialogue.add("user", user_input)
        self.events.emit("UserMessageReceived", content=user_input)

        decision = self.compass.decide(user_input, requires_confirmation=requires_confirmation)
        self.events.emit(
            "CompassDecisionMade",
            decision=decision.type.value,
            reason=decision.reason,
        )

        metadata: dict[str, Any] = {}

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
            output, metadata = self._handle_agent_output(result.output)
        else:
            result = self.agent.run(user_input, context={"decision": decision.type.value})
            output, metadata = self._handle_agent_output(result.output)

        self.dialogue.add("agent", output)
        self.events.emit("AgentResponded", content=output)
        return NavigationResult(output=output, decision=decision.type.value, metadata=metadata)

    def stream(
        self,
        user_input: str,
        *,
        requires_confirmation: bool = False,
    ):
        """Yield high-level events for one navigation turn."""

        yield StreamEvent(
            type="start",
            data={"input": user_input},
        )
        result = self.navigate(user_input, requires_confirmation=requires_confirmation)
        yield StreamEvent(
            type="result",
            data={
                "output": result.output,
                "decision": result.decision,
                "metadata": to_jsonable(result.metadata),
            },
        )

        tool_result = result.metadata.get("tool_result")
        if tool_result and getattr(tool_result, "requires_confirmation", False):
            checkpoint = getattr(tool_result, "checkpoint", None)
            yield StreamEvent(
                type="checkpoint",
                data={
                    "checkpoint": checkpoint.to_dict() if checkpoint else None,
                    "tool": getattr(tool_result, "name", None),
                },
            )

        yield StreamEvent(type="done", data={"output": result.output})

    def _handle_agent_output(self, output: str) -> tuple[str, dict[str, Any]]:
        action = parse_agent_action(output)
        self.events.emit("AgentActionParsed", action=action.type.value)

        if action.type == AgentActionType.TOOL_CALL:
            if action.tool is None:
                return output, {"agent_action": action}

            tool_result = self.call_tool(action.tool, *action.args, **action.kwargs)
            if tool_result.requires_confirmation:
                message = (
                    f"Confirmation required before running tool {tool_result.name!r}: "
                    f"{tool_result.checkpoint.reason}"
                )
            else:
                message = str(tool_result.output)

            return message, {
                "agent_action": action,
                "tool_result": tool_result,
            }

        if action.type == AgentActionType.STOP:
            return action.content or "Stopped.", {"agent_action": action}

        if action.raw != output:
            return action.content, {"agent_action": action}

        return output, {}

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

    def call_tool(self, name: str, *args: Any, **kwargs: Any) -> ToolResult:
        tool = self.agent.get_tool(name)
        if tool is None:
            raise ToolNotFound(f"Agent {self.agent.name!r} does not have tool {name!r}.")

        action = tool.action or "tool_call"
        call = ToolCall(
            name=tool.name,
            args=args,
            kwargs=kwargs,
            risk=tool.risk,
            action=action,
        )
        self.events.emit(
            "ToolCallRequested",
            tool=call.name,
            action=call.action,
            risk=call.risk,
        )

        if self.policy.requires_confirmation(action=call.action, risk=call.risk):
            checkpoint = self.checkpoint(
                reason=f"Tool {call.name!r} requires confirmation before execution.",
                action=call.action,
                payload={
                    "kind": "tool_call",
                    "tool": call.name,
                    "args": list(call.args),
                    "kwargs": call.kwargs,
                    "risk": call.risk,
                },
            )
            self.pending_tool_calls[checkpoint.id] = call
            self.events.emit(
                "ToolCallPaused",
                tool=call.name,
                checkpoint_id=checkpoint.id,
            )
            return ToolResult(
                name=call.name,
                requires_confirmation=True,
                checkpoint=checkpoint,
                metadata={"risk": call.risk, "action": call.action},
            )

        result = tool(*call.args, **call.kwargs)
        self.events.emit("ToolCallCompleted", tool=call.name)
        return result

    def approve_checkpoint(self, checkpoint_id: str) -> Checkpoint:
        checkpoint = self.get_checkpoint(checkpoint_id)
        checkpoint.approve()
        self.events.emit("CheckpointApproved", checkpoint_id=checkpoint.id)
        return checkpoint

    def reject_checkpoint(self, checkpoint_id: str) -> Checkpoint:
        checkpoint = self.get_checkpoint(checkpoint_id)
        checkpoint.reject()
        self.events.emit("CheckpointRejected", checkpoint_id=checkpoint.id)
        return checkpoint

    def resume_checkpoint(self, checkpoint_id: str) -> ToolResult:
        checkpoint = self.get_checkpoint(checkpoint_id)
        if checkpoint.status == CheckpointStatus.REJECTED:
            raise CheckpointRejected(f"Checkpoint {checkpoint_id!r} was rejected.")
        if checkpoint.status != CheckpointStatus.APPROVED:
            raise CheckpointNotApproved(f"Checkpoint {checkpoint_id!r} is not approved.")

        call = self.pending_tool_calls.get(checkpoint.id)
        if call is None:
            raise CheckpointNotFound(
                f"Checkpoint {checkpoint_id!r} does not have a pending tool call."
            )

        tool = self.agent.get_tool(call.name)
        if tool is None:
            raise ToolNotFound(f"Agent {self.agent.name!r} does not have tool {call.name!r}.")

        self.events.emit("CheckpointResumed", checkpoint_id=checkpoint.id, tool=call.name)
        result = tool(*call.args, **call.kwargs)
        self.events.emit("ToolCallCompleted", tool=call.name, checkpoint_id=checkpoint.id)
        del self.pending_tool_calls[checkpoint.id]
        return result

    def resume_workflow(self, checkpoint_id: str) -> WorkflowResult:
        checkpoint = self.get_checkpoint(checkpoint_id)
        if checkpoint.status == CheckpointStatus.REJECTED:
            raise CheckpointRejected(f"Checkpoint {checkpoint_id!r} was rejected.")
        if checkpoint.status != CheckpointStatus.APPROVED:
            raise CheckpointNotApproved(f"Checkpoint {checkpoint_id!r} is not approved.")

        pending = self.pending_workflows.get(checkpoint.id)
        if pending is None:
            raise CheckpointNotFound(
                f"Checkpoint {checkpoint_id!r} does not have a pending workflow."
            )

        self.events.emit(
            "WorkflowResumed",
            workflow=pending.workflow.name,
            checkpoint_id=checkpoint.id,
        )
        result = self._run_workflow(
            pending.workflow,
            pending.state,
            start_at=pending.next_step,
            completed=pending.completed_steps,
        )
        if not result.paused:
            self.events.emit(
                "WorkflowCompleted",
                workflow=pending.workflow.name,
                steps=result.steps,
            )
        del self.pending_workflows[checkpoint.id]
        return result

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint:
        for checkpoint in self.checkpoints:
            if checkpoint.id == checkpoint_id:
                return checkpoint
        raise CheckpointNotFound(f"Checkpoint {checkpoint_id!r} was not found.")

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-safe audit snapshot of the session."""

        return {
            "agent": {
                "name": self.agent.name,
                "tools": self.agent.tool_manifest(),
            },
            "dialogue": self.dialogue.to_dict(),
            "events": self.events.to_list(),
            "checkpoints": [checkpoint.to_dict() for checkpoint in self.checkpoints],
            "pending_tool_calls": {
                checkpoint_id: call.to_dict()
                for checkpoint_id, call in self.pending_tool_calls.items()
            },
            "pending_workflows": {
                checkpoint_id: pending.to_dict()
                for checkpoint_id, pending in self.pending_workflows.items()
            },
        }

    def save_snapshot(self, path: str | Path) -> Path:
        """Save the current session snapshot to a JSON file."""

        return save_snapshot(self.snapshot(), path)

    def run(self, workflow: Workflow, value: Any) -> WorkflowResult:
        self.events.emit("WorkflowStarted", workflow=workflow.name)
        result = self._run_workflow(workflow, value)
        if not result.paused:
            self.events.emit("WorkflowCompleted", workflow=workflow.name, steps=result.steps)
        return result

    def _run_workflow(
        self,
        workflow: Workflow,
        value: Any,
        *,
        start_at: int = 0,
        completed: list[str] | None = None,
    ) -> WorkflowResult:
        result = workflow.run(value, start_at=start_at, completed=completed)
        if result.paused:
            checkpoint = self.checkpoint(
                reason=str(result.metadata.get("reason") or "Workflow checkpoint."),
                action="workflow_checkpoint",
                payload={
                    "kind": "workflow",
                    "workflow": workflow.name,
                    "step": result.metadata.get("step"),
                    "current_step": result.current_step,
                },
            )
            self.pending_workflows[checkpoint.id] = PendingWorkflow(
                workflow=workflow,
                state=result.state,
                next_step=(result.current_step or 0) + 1,
                completed_steps=result.steps,
            )
            self.events.emit(
                "WorkflowPaused",
                workflow=workflow.name,
                checkpoint_id=checkpoint.id,
            )
            return WorkflowResult(
                name=result.name,
                output=result.output,
                steps=result.steps,
                paused=True,
                checkpoint=checkpoint,
                current_step=result.current_step,
                state=result.state,
                metadata=result.metadata,
            )

        return result
