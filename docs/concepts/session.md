# Session

`Session` is the human-agent working context in Pyxis.

It owns the conversation state, compass decisions, checkpoints, event log,
pending tool calls, pending workflows, and audit snapshots. Prefer
`Session.navigate()` over calling `Agent.run()` directly when you want Pyxis to
keep the human in control.

```python
from pyxis import Agent, Pyxis

session = Pyxis(agent=Agent(name="navigator")).session()
result = session.navigate("Plan a controlled research workflow")

print(result.decision)
print(result.output)
print(session.dialogue.intent)
```

## What A Session Records

- `dialogue`: messages plus structured intent, goal, clarifications, constraints,
  and preferences.
- `events`: observable state changes for audit and debugging.
- `checkpoints`: human approval points before sensitive actions.
- `pending_tool_calls`: paused tool calls waiting for approval.
- `pending_workflows`: paused workflows waiting for approval.
- `memory`: bounded preferences, project context, and scratchpad state.

## Streaming

`Session.stream()` always yields `start`, `result`, and `done` events. When the
provider supports native streaming, it also yields `delta` events before the
final result.

```python
for event in session.stream("Draft a concise plan"):
    if event.type == "delta":
        print(event.data["text"], end="")
```

## Snapshots

Sessions can produce JSON-safe snapshots for inspection:

```python
snapshot = session.snapshot(redact=True)
session.save_snapshot("session-audit.json", redact=True)
```

Use redaction when snapshots may include prompts, tool payloads, provider
metadata, or memory values that should not be exported in plain text.
