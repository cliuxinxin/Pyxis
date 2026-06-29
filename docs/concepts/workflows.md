# Workflows

`Workflow` is a small observable sequence of steps.

It is intentionally simple: callables transform state, and session-managed pause
steps ask for human approval or calibration.

```python
from pyxis import Workflow

workflow = (
    Workflow("draft")
    .step("clean", lambda text: text.strip())
    .step("report", lambda text: f"Report: {text}")
)

result = workflow.run("  Pyxis keeps work controllable.  ")
print(result.output)
```

## Checkpointed Workflows

Run workflows through a `Session` when you want checkpoint and resume support:

```python
workflow = (
    Workflow("draft")
    .step("clean", lambda text: text.strip())
    .checkpoint("Review cleaned text before writing the report.")
    .step("report", lambda text: f"Report: {text}")
)

result = session.run(workflow, "  Pyxis  ")
if result.paused:
    session.approve_checkpoint(result.checkpoint.id)
    result = session.resume_workflow(result.checkpoint.id)
```

## Reflective Steps

Reflective workflows can pause for calibration:

```python
workflow = (
    Workflow("guided-draft")
    .step("clean", lambda text: text.strip())
    .reflect("Check if the output matches the user's goal")
    .ask("Does this direction look right?")
    .revise("What should change before the final draft?")
    .step("finish", lambda text: f"Final: {text}")
)
```

These steps use the same checkpoint/resume flow, but their metadata describes
the pause as direction, reflection, or revision rather than a generic gate.
