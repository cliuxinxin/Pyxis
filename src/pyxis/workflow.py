"""Simple observable workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pyxis.results import WorkflowResult


@dataclass(frozen=True)
class WorkflowStep:
    """A named callable step."""

    name: str
    fn: Callable[[Any], Any]


@dataclass
class Workflow:
    """A minimal sequential workflow."""

    name: str
    steps: list[WorkflowStep] = field(default_factory=list)

    def step(self, name: str, fn: Callable[[Any], Any]) -> Workflow:
        self.steps.append(WorkflowStep(name=name, fn=fn))
        return self

    def run(self, value: Any) -> WorkflowResult:
        current = value
        completed: list[str] = []
        for step in self.steps:
            current = step.fn(current)
            completed.append(step.name)
        return WorkflowResult(name=self.name, output=current, steps=completed)
