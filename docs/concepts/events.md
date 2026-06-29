# Events

Pyxis sessions keep an append-only event log for audit, debugging, snapshots,
and host application observability.

Each event has a stable envelope:

- `id`: unique event id.
- `type`: stable event name.
- `payload`: JSON-safe event data.
- `created_at`: ISO timestamp.
- `schema_version`: event schema version.

The public event catalog is available as `EVENT_SCHEMAS`.

```python
from pyxis import EVENT_SCHEMAS

print(EVENT_SCHEMAS["ProviderStarted"].required)
```

`EventLog.emit()` validates required payload keys for known Pyxis events.
Unknown event names are allowed so applications can append their own local
events without forking the core.

## Stable Event Families

Provider events:

- `ProviderStarted`: `agent`, `provider`, `mode`.
- `ProviderDone`: `agent`, `provider`, `mode`, with optional `finish_reason`,
  `usage`, and `chunks`.
- `ProviderError`: `agent`, `provider`, `mode`, `error`, `message`.

Tool events:

- `ToolValidationFailed`: `tool`, `error`.
- `ToolCallRequested`: `tool`, `action`, `risk`.
- `ToolCallPaused`: `tool`, `checkpoint_id`, optional `policy_reason`.
- `ToolCallCompleted`: `tool`, optional `checkpoint_id`.

Checkpoint and policy events:

- `CheckpointCreated`: `checkpoint_id`, `reason`, `action`.
- `CheckpointApproved`: `checkpoint_id`.
- `CheckpointRejected`: `checkpoint_id`.
- `CheckpointResumed`: `checkpoint_id`, optional `tool`.
- `PolicyDenied`: `tool`, `action`, `reason`.

Workflow events:

- `WorkflowStarted`: `workflow`.
- `WorkflowStepStarted`: `workflow`, `step`, `index`, `kind`.
- `WorkflowStepCompleted`: `workflow`, `step`, `index`, `kind`.
- `WorkflowStepFailed`: `workflow`, `step`, `index`, `kind`, `error`,
  `message`.
- `WorkflowPaused`: `workflow`, `checkpoint_id`.
- `WorkflowResumed`: `workflow`, `checkpoint_id`.
- `WorkflowCompleted`: `workflow`, `steps`.

Session events:

- `UserMessageReceived`: `content`.
- `CompassDecisionMade`: `decision`, `reason`, `intent`,
  `needs_clarification`.
- `AgentActionParsed`: `action`.
- `AgentResponded`: `content`.
- `SessionRestored`: `checkpoints`.
