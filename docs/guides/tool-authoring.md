# Tool Authoring Guide

Tools are explicit capabilities that an agent can request through Pyxis'
controlled action protocol.

## Define A Tool

```python
from pyxis import tool

@tool(risk="low", action="summarize")
def summarize(text: str, max_words: int = 50) -> str:
    return " ".join(text.split()[:max_words])
```

Choose:

- `risk`: `low`, `medium`, or `high`.
- `action`: stable policy category, such as `file_write`, `network_post`, or
  `summarize`.
- docstring: short human-readable description for the tool manifest.

## Validation

Pyxis validates tool arguments before execution. Validation catches:

- missing required arguments
- unexpected arguments
- duplicate positional and keyword arguments
- common annotation mismatches
- invalid `typing.Literal` values

Invalid calls raise `ToolValidationError` before user tool code runs.

## Model Action Shape

The recommended model output shape is:

```json
{"type":"tool_call","tool":"summarize","args":{"text":"Pyxis"}}
```

Use normal text when no tool is needed.

## Policy And Checkpoints

Policy uses `action` and `risk` to decide whether to run, pause, or deny:

```python
from pyxis import ControlPolicy

policy = ControlPolicy(
    deny_actions={"payment"},
    risk_overrides={"file_write": "high"},
)
```

High-risk tools usually produce a checkpoint before execution. The host
application can approve, reject, inspect, or persist that checkpoint.

## Snapshot Restore

Snapshots store tool names and pending arguments, not Python callables. To resume
a pending tool call, register the tool:

```python
from pyxis import SnapshotRestoreCatalog, restore_session

session = restore_session(
    snapshot,
    catalog=SnapshotRestoreCatalog(tools={"summarize": summarize}),
)
```

This keeps restore explicit and avoids importing arbitrary code from a snapshot.
