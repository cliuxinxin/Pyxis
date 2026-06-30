# Cookbook

This cookbook shows small Pyxis patterns that compose into controllable agent
workflows.

## Run A Provider-Backed Session

```python
import os

from pyxis import Agent, OpenAICompatibleProvider, Pyxis

provider = OpenAICompatibleProvider(model=os.environ["OPENAI_MODEL"])
session = Pyxis(agent=Agent(name="navigator", provider=provider)).session()

result = session.navigate("Draft a concise release checklist")
print(result.output)
```

## Stream A Response

```python
for event in session.stream("Draft a concise plan"):
    if event.type == "delta":
        print(event.data["text"], end="")
```

## Get Structured JSON

```python
schema = {
    "type": "object",
    "required": ["importance", "reason"],
    "properties": {
        "importance": {"type": "number"},
        "reason": {"type": "string"},
    },
}

result = session.structured_run(
    "Score this signal",
    schema=schema,
    max_retries=1,
)

if result.valid:
    print(result.output["importance"])
else:
    print(result.errors)
```

## Add A Controlled Tool

```python
from pyxis import Agent, Pyxis, tool

@tool(risk="high", action="file_write")
def write_file(path: str, content: str) -> str:
    return f"would write {len(content)} characters to {path}"

session = Pyxis(agent=Agent(name="navigator", tools=[write_file])).session()
result = session.call_tool("write_file", "notes.txt", content="hello")

if result.requires_confirmation:
    checkpoint = result.checkpoint
    print(checkpoint.summary)
```

## Restore A Pending Tool Call

```python
from pyxis import SnapshotRestoreCatalog, load_snapshot, restore_session

snapshot = load_snapshot("session-audit.json")
session = restore_session(
    snapshot,
    catalog=SnapshotRestoreCatalog(tools={"write_file": write_file}),
)
```

## Use A Strict Policy

```python
from pyxis import ControlPolicy, Pyxis

pyxis = Pyxis(agent=agent, policy=ControlPolicy.strict())
```

## Save A Redacted Snapshot

```python
from pyxis import SnapshotRedactionPolicy

policy = SnapshotRedactionPolicy(redact_keys={"api_key", "customer_email"})
session.save_snapshot("session-audit.json", redact=True, redaction_policy=policy)
```

## Inspect Events

```python
for event in session.events:
    print(event.type, event.payload)
```

Use `EVENT_SCHEMAS` when building a host UI or log exporter that needs stable
payload contracts.

## Attach An Event Sink

```python
from pyxis import Agent, EventLog, InMemoryEventSink, Session

sink = InMemoryEventSink()
session = Session(
    agent=Agent(name="navigator"),
    events=EventLog(sinks=[sink]),
)

session.navigate("Draft a concise plan")
print(sink.to_list())
```

## Keep Long-Term Preferences

```python
from pyxis import InMemoryStore

store = InMemoryStore()
store.set(
    "user",
    "watchlist",
    ["agent frameworks", "AI infrastructure"],
    metadata={"source": "explicit_feedback"},
)

topics = store.get("user", "watchlist", default=[])
```

Use the `MemoryStore` protocol for product-level memory. Database-backed stores
belong in the host application or an extension package.

## Call Pyxis From A Scheduler

```python
def run_daily_briefing():
    session = build_session()
    return session.structured_run(
        "Generate today's briefing",
        schema=briefing_schema,
        max_retries=1,
    )
```

The scheduler owns when this function runs. Pyxis owns the controllable agent
work inside the function.
