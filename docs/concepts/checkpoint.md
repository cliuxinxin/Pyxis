# Checkpoint

`Checkpoint` is Pyxis' consent primitive.

It is created when a session reaches an action that should not run silently:
high-risk tools, workflow pauses, explicit confirmation gates, or reflective
workflow calibration.

```python
checkpoint = session.checkpoint(
    reason="This may modify local files.",
    action="file_write",
    summary="Pyxis wants to run a high-risk action.",
    risk_reason="This may modify local files.",
    preview="notes.txt",
)
```

## User-Facing Fields

- `summary`: short description of what Pyxis wants to do.
- `action`: machine-readable action name, such as `file_write`.
- `risk_reason`: why this needs confirmation.
- `preview`: compact preview of the target or operation.
- `options`: approval choices, currently `approve` and `reject` by default.
- `status`: `pending`, `approved`, or `rejected`.

## Policy Decisions

Checkpoints are created from `ControlPolicy` decisions.

```python
from pyxis import ControlPolicy

policy = ControlPolicy(
    approval_mode="strict",
    deny_actions={"payment"},
    risk_overrides={"file_write": "high"},
    checkpoint_options=["approve", "reject", "revise"],
)
```

Policy supports:

- `approval_mode`: `permissive`, `balanced`, or `strict`.
- `allow_auto_for_actions`: actions allowed to run without a checkpoint.
- `deny_actions`: actions blocked before execution.
- `risk_overrides`: action-specific effective risk.
- `checkpoint_options`: choices copied into created checkpoints.

Denied actions raise `PolicyDeniedError` instead of creating a checkpoint.

## Approval Flow

```python
paused = session.call_tool("write_file", "notes.txt", content="hello")
checkpoint = paused.checkpoint

session.approve_checkpoint(checkpoint.id)
result = session.resume_checkpoint(checkpoint.id)
```

Rejecting a checkpoint prevents resume:

```python
session.reject_checkpoint(checkpoint.id)
```

## CLI Consent Prompt

When a CLI run creates a checkpoint, Pyxis shows the same consent details:

```text
Pyxis wants to run a high-risk action.

Action: file_write
Reason: This may modify local files.
Preview: notes.txt

Approve? [y/N]
```
