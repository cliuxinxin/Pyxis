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
