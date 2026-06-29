"""Simple observable workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pyxis.results import WorkflowResult


class WorkflowStepKind(str, Enum):
    """Kinds of workflow steps."""

    CALLABLE = "callable"
    CHECKPOINT = "checkpoint"


@dataclass(frozen=True)
class WorkflowStep:
    """A workflow step."""

    name: str
    fn: Callable[[Any], Any] | None = None
    kind: WorkflowStepKind = WorkflowStepKind.CALLABLE
    reason: str = ""


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
            if step.kind == WorkflowStepKind.CHECKPOINT:
                return WorkflowResult(
                    name=self.name,
                    output=current,
                    steps=completed_steps,
                    paused=True,
                    current_step=index,
                    state=current,
                    metadata={"reason": step.reason, "step": step.name},
                )

            if step.fn is None:
                raise TypeError(f"Workflow step {step.name!r} does not have a callable.")
            current = step.fn(current)
            completed_steps.append(step.name)
        return WorkflowResult(name=self.name, output=current, steps=completed_steps, state=current)
