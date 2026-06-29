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
from pyxis.errors import (
    CheckpointNotApproved,
    CheckpointNotFound,
    CheckpointRejected,
    PolicyDeniedError,
    ToolNotFound,
    ToolValidationError,
)
from pyxis.events import EventLog
from pyxis.policy import ControlPolicy
from pyxis.results import NavigationResult, StreamEvent, ToolResult, WorkflowResult
from pyxis.serialization import redact_jsonable, to_jsonable
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

        analysis = self.compass.analyze(
            user_input,
            requires_confirmation=requires_confirmation,
        )
        decision = analysis.decision
        self._record_analysis(analysis)
        self.events.emit(
            "CompassDecisionMade",
            decision=decision.type.value,
            reason=decision.reason,
            intent=analysis.intent.type.value,
            needs_clarification=analysis.intent.needs_clarification,
        )

        metadata: dict[str, Any] = {"analysis": analysis}

        if decision.type == CompassDecisionType.ASK_CLARIFICATION:
            output = decision.prompt or "Can you clarify what you want to do next?"
        elif decision.type == CompassDecisionType.STOP:
            output = "Stopped."
        elif decision.type == CompassDecisionType.REQUEST_CONFIRMATION:
            checkpoint = self.checkpoint(
                reason=decision.reason,
                action="navigation",
                payload={"input": user_input},
                summary="Pyxis needs confirmation before continuing this navigation step.",
                risk_reason=decision.reason,
                preview=user_input,
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

    def _record_analysis(self, analysis: Any) -> None:
        self.dialogue.intent = analysis.intent
        if analysis.goal is not None:
            self.dialogue.goal = analysis.goal
            self.dialogue.user_goal = analysis.goal.text
        for constraint in analysis.constraints:
            if constraint not in self.dialogue.constraints:
                self.dialogue.constraints.append(constraint)
        self.dialogue.preferences.update(analysis.preferences)
        if analysis.clarification is not None:
            self.dialogue.clarifications.append(analysis.clarification)
            self.dialogue.open_questions.append(analysis.clarification.question)

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

        if self._can_stream_provider():
            result = yield from self._stream_with_provider(
                user_input,
                requires_confirmation=requires_confirmation,
            )
            yield from self._stream_result_events(result)
            return

        result = self.navigate(user_input, requires_confirmation=requires_confirmation)
        yield from self._stream_result_events(result)

    def _stream_result_events(self, result: NavigationResult):
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

    def _stream_with_provider(
        self,
        user_input: str,
        *,
        requires_confirmation: bool = False,
    ):
        self.dialogue.add("user", user_input)
        self.events.emit("UserMessageReceived", content=user_input)

        analysis = self.compass.analyze(
            user_input,
            requires_confirmation=requires_confirmation,
        )
        decision = analysis.decision
        self._record_analysis(analysis)
        self.events.emit(
            "CompassDecisionMade",
            decision=decision.type.value,
            reason=decision.reason,
            intent=analysis.intent.type.value,
            needs_clarification=analysis.intent.needs_clarification,
        )

        metadata: dict[str, Any] = {"analysis": analysis}

        if decision.type == CompassDecisionType.ASK_CLARIFICATION:
            output = decision.prompt or "Can you clarify what you want to do next?"
        elif decision.type == CompassDecisionType.STOP:
            output = "Stopped."
        elif decision.type == CompassDecisionType.REQUEST_CONFIRMATION:
            checkpoint = self.checkpoint(
                reason=decision.reason,
                action="navigation",
                payload={"input": user_input},
                summary="Pyxis needs confirmation before continuing this navigation step.",
                risk_reason=decision.reason,
                preview=user_input,
            )
            output = f"Confirmation required before continuing: {checkpoint.reason}"
        else:
            if decision.type == CompassDecisionType.PROPOSE_PLAN:
                prompt = f"Propose a concise, controllable plan for this request:\n{user_input}"
            else:
                prompt = user_input
            chunks: list[str] = []
            for chunk in self.agent.stream(prompt, context={"decision": decision.type.value}):
                if not chunk.text:
                    continue
                chunks.append(chunk.text)
                yield StreamEvent(
                    type="delta",
                    data={
                        "text": chunk.text,
                        "metadata": to_jsonable(chunk.metadata),
                    },
                )
            output = self.agent.response_style.apply("".join(chunks))
            output, action_metadata = self._handle_agent_output(output)
            metadata.update(action_metadata)
            metadata["streamed"] = True

        self.dialogue.add("agent", output)
        self.events.emit("AgentResponded", content=output)
        return NavigationResult(output=output, decision=decision.type.value, metadata=metadata)

    def _can_stream_provider(self) -> bool:
        return callable(getattr(self.agent.provider, "stream", None))

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
        summary: str | None = None,
        risk_reason: str | None = None,
        preview: str | None = None,
        options: list[str] | None = None,
    ) -> Checkpoint:
        checkpoint = Checkpoint(
            reason=reason,
            action=action,
            payload=payload or {},
            summary=summary,
            risk_reason=risk_reason,
            preview=preview,
            options=options or ["approve", "reject"],
        )
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

        try:
            tool.validate_arguments(*args, **kwargs)
        except ToolValidationError as exc:
            self.events.emit("ToolValidationFailed", tool=tool.name, error=str(exc))
            raise

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

        decision = self.policy.decide(action=call.action, risk=call.risk)
        if not decision.allowed:
            self.events.emit(
                "PolicyDenied",
                tool=call.name,
                action=call.action,
                reason=decision.reason,
            )
            raise PolicyDeniedError(decision.reason)

        if decision.requires_confirmation:
            checkpoint = self.checkpoint(
                reason=f"Tool {call.name!r} requires confirmation before execution.",
                action=call.action,
                payload={
                    "kind": "tool_call",
                    "tool": call.name,
                    "args": list(call.args),
                    "kwargs": call.kwargs,
                    "risk": call.risk,
                    "effective_risk": decision.effective_risk,
                    "policy_reason": decision.reason,
                },
                summary=f"Pyxis wants to run tool {call.name!r}.",
                risk_reason=decision.reason,
                preview=self._preview_tool_call(call),
                options=decision.options,
            )
            self.pending_tool_calls[checkpoint.id] = call
            self.events.emit(
                "ToolCallPaused",
                tool=call.name,
                checkpoint_id=checkpoint.id,
                policy_reason=decision.reason,
            )
            return ToolResult(
                name=call.name,
                requires_confirmation=True,
                checkpoint=checkpoint,
                metadata={
                    "risk": call.risk,
                    "effective_risk": decision.effective_risk,
                    "action": call.action,
                    "policy_reason": decision.reason,
                },
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

    def snapshot(self, *, redact: bool = False) -> dict[str, Any]:
        """Return a JSON-safe audit snapshot of the session."""

        snapshot = {
            "agent": {
                "name": self.agent.name,
                "tools": self.agent.tool_manifest(),
                "memory": self._memory_snapshot(),
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
        if redact:
            return redact_jsonable(snapshot)
        return snapshot

    def _memory_snapshot(self) -> dict[str, Any]:
        to_dict = getattr(self.agent.memory, "to_dict", None)
        if callable(to_dict):
            return to_jsonable(to_dict())
        return {}

    def save_snapshot(self, path: str | Path, *, redact: bool = False) -> Path:
        """Save the current session snapshot to a JSON file."""

        return save_snapshot(self.snapshot(redact=redact), path)

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
            step_kind = str(result.metadata.get("kind") or "checkpoint")
            prompt = str(result.metadata.get("prompt") or "")
            step_name = str(result.metadata.get("step") or step_kind)
            reason = str(result.metadata.get("reason") or "Workflow checkpoint.")
            checkpoint = self.checkpoint(
                reason=reason,
                action=f"workflow_{step_kind}",
                payload={
                    "kind": "workflow",
                    "step_kind": step_kind,
                    "workflow": workflow.name,
                    "step": step_name,
                    "prompt": prompt,
                    "current_step": result.current_step,
                },
                summary=self._workflow_checkpoint_summary(workflow.name, step_kind),
                risk_reason=reason,
                preview=prompt or step_name,
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

    def _workflow_checkpoint_summary(self, workflow_name: str, step_kind: str) -> str:
        if step_kind == "ask":
            return f"Workflow {workflow_name!r} wants to ask for direction."
        if step_kind == "reflect":
            return f"Workflow {workflow_name!r} wants to reflect before continuing."
        if step_kind == "revise":
            return f"Workflow {workflow_name!r} wants to revise before continuing."
        return f"Workflow {workflow_name!r} paused for confirmation."

    def _preview_tool_call(self, call: ToolCall) -> str:
        arguments: list[str] = []
        if call.args:
            arguments.extend(repr(arg) for arg in call.args[:3])
        if call.kwargs:
            kwargs = list(call.kwargs.items())[:3]
            arguments.extend(f"{key}={value!r}" for key, value in kwargs)
        if not arguments:
            return call.name
        return f"{call.name}({', '.join(arguments)})"
