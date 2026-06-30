"""Simple observable workflows."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pyxis.results import WorkflowResult


class WorkflowStepKind(str, Enum):
    """Kinds of workflow steps."""

    CALLABLE = "callable"
    CHECKPOINT = "checkpoint"
    ASK = "ask"
    REFLECT = "reflect"
    REVISE = "revise"


@dataclass(frozen=True)
class WorkflowStep:
    """A workflow step."""

    name: str
    fn: Callable[[Any], Any] | None = None
    kind: WorkflowStepKind = WorkflowStepKind.CALLABLE
    reason: str = ""
    prompt: str = ""


@dataclass
class Workflow:
    """A minimal sequential workflow."""

    name: str
    steps: list[WorkflowStep] = field(default_factory=list)

    def step(self, name: str, fn: Callable[[Any], Any]) -> Workflow:
        self.steps.append(WorkflowStep(name=name, fn=fn))
        return self

    def checkpoint(self, reason: str, *, name: str | None = None) -> Workflow:
        self.steps.append(
            WorkflowStep(
                name=name or "checkpoint",
                kind=WorkflowStepKind.CHECKPOINT,
                reason=reason,
            )
        )
        return self

    def ask(self, prompt: str, *, name: str | None = None) -> Workflow:
        """Pause the workflow to ask the user for direction."""

        self.steps.append(
            WorkflowStep(
                name=name or "ask",
                kind=WorkflowStepKind.ASK,
                reason="Workflow needs user direction.",
                prompt=prompt,
            )
        )
        return self

    def reflect(self, prompt: str, *, name: str | None = None) -> Workflow:
        """Pause the workflow to check whether the current output is useful."""

        self.steps.append(
            WorkflowStep(
                name=name or "reflect",
                kind=WorkflowStepKind.REFLECT,
                reason="Workflow paused for reflection.",
                prompt=prompt,
            )
        )
        return self

    def revise(self, prompt: str, *, name: str | None = None) -> Workflow:
        """Pause the workflow to let the user redirect or revise the work."""

        self.steps.append(
            WorkflowStep(
                name=name or "revise",
                kind=WorkflowStepKind.REVISE,
                reason="Workflow paused for revision.",
                prompt=prompt,
            )
        )
        return self

    def run(
        self,
        value: Any,
        *,
        start_at: int = 0,
        completed: list[str] | None = None,
    ) -> WorkflowResult:
        current = value
        completed_steps = list(completed or [])
        for index in range(start_at, len(self.steps)):
            step = self.steps[index]
            if step.kind != WorkflowStepKind.CALLABLE:
                return WorkflowResult(
                    name=self.name,
                    output=current,
                    steps=completed_steps,
                    paused=True,
                    current_step=index,
                    state=current,
                    metadata={
                        "kind": step.kind.value,
                        "reason": step.reason,
                        "step": step.name,
                        "prompt": step.prompt,
                    },
                )

            if step.fn is None:
                raise TypeError(f"Workflow step {step.name!r} does not have a callable.")
            if inspect.iscoroutinefunction(step.fn):
                raise TypeError(
                    f"Workflow step {step.name!r} is async. Use Workflow.arun() "
                    "or Session.arun()."
                )
            output = step.fn(current)
            if inspect.isawaitable(output):
                close = getattr(output, "close", None)
                if callable(close):
                    close()
                raise TypeError(
                    f"Workflow step {step.name!r} returned an awaitable. "
                    "Use Workflow.arun() or Session.arun()."
                )
            current = output
            completed_steps.append(step.name)
        return WorkflowResult(name=self.name, output=current, steps=completed_steps, state=current)

    async def arun(
        self,
        value: Any,
        *,
        start_at: int = 0,
        completed: list[str] | None = None,
    ) -> WorkflowResult:
        current = value
        completed_steps = list(completed or [])
        for index in range(start_at, len(self.steps)):
            step = self.steps[index]
            if step.kind != WorkflowStepKind.CALLABLE:
                return WorkflowResult(
                    name=self.name,
                    output=current,
                    steps=completed_steps,
                    paused=True,
                    current_step=index,
                    state=current,
                    metadata={
                        "kind": step.kind.value,
                        "reason": step.reason,
                        "step": step.name,
                        "prompt": step.prompt,
                    },
                )

            if step.fn is None:
                raise TypeError(f"Workflow step {step.name!r} does not have a callable.")
            current = step.fn(current)
            if inspect.isawaitable(current):
                current = await current
            completed_steps.append(step.name)
        return WorkflowResult(name=self.name, output=current, steps=completed_steps, state=current)
