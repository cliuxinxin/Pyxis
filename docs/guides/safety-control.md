# Safety And Control Guide

Pyxis treats control as a first-class runtime contract.

The main pieces are:

- `ControlPolicy`: decides whether an action is allowed, auto-runnable, or needs
  confirmation.
- `Checkpoint`: records the human-facing approval request.
- `Session`: enforces the policy before tools or workflows continue.

## Approval Modes

```python
from pyxis import ControlPolicy

balanced = ControlPolicy.safe_default()
strict = ControlPolicy.strict()
permissive = ControlPolicy.permissive()
```

- `balanced`: the default. High-risk actions and known sensitive actions require
  confirmation, while explicitly safe actions can run automatically.
- `strict`: every action requires confirmation unless explicitly listed in
  `allow_auto_for_actions`.
- `permissive`: only explicit policy rules require confirmation.

## Deny List

Use `deny_actions` for actions that must not run in the current application:

```python
policy = ControlPolicy(deny_actions={"payment", "shell_exec"})
```

Denied actions raise `PolicyDeniedError` before a checkpoint is created.

## Risk Overrides

Use `risk_overrides` when the same tool action has different risk in your
application:

```python
policy = ControlPolicy(
    risk_overrides={"file_write": "high"},
)
```

The original tool risk is still recorded, but the effective risk drives the
policy decision.

## Checkpoint Options

Applications can expose additional choices:

```python
policy = ControlPolicy(
    checkpoint_options=["approve", "reject", "revise"],
)
```

Pyxis stores these options on each checkpoint so a CLI, web UI, or host
application can render the same consent surface.

## Recommended Defaults

Use `ControlPolicy.safe_default()` unless your host application has a clearer
policy. It requires confirmation for high-risk work and known sensitive actions
such as file writes, shell execution, payments, and network posts.
