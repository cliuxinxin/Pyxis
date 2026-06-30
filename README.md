# Pyxis

A minimal, human-centered Python agent harness for building controllable AI
workflows.

Pyxis is named after the mariner's compass constellation. It is built around a
simple idea:

> The conversation is the control surface, and the human stays in the loop.

Use Pyxis when you want an agent workflow that can act, but can also pause,
explain, resume, stream, record events, save snapshots, and keep risky actions
under human control.

## What You Get

- A small `Session` runtime for dialogue, tools, checkpoints, workflows, memory,
  events, and snapshots.
- Controlled tool calls with argument validation before user code runs.
- Human approval through `Checkpoint` and configurable `ControlPolicy`.
- Restorable JSON snapshots through explicit tool and workflow catalogs.
- OpenAI-compatible provider support with common `OPENAI_*` environment
  variables, SSE streaming, usage, finish reasons, retries, timeout, and
  cancellation.
- Stable event schemas for provider, tool, checkpoint, policy, workflow, and
  restore observability, with optional event sinks for host storage or UIs.
- Structured JSON output helpers for lightweight schema-constrained results.
- Async tools, providers, and workflows for IO-heavy host applications.
- Long-term memory store protocols that host applications can back with their
  own storage.
- A practical CLI for demo, run, stream, inspect, memory, and workflow smoke
  tests.
- A PyTorch-like control style: use `navigate()` for the default path, or split
  the turn into analysis, prompt building, provider calls, action dispatch, and
  response recording.

## Install

From PyPI:

```bash
pip install pyxis-ai
```

For local development from this repository:

```bash
pip install -e ".[dev]"
```

Pyxis has no required model SDK dependency.

## Try It Locally

Run a no-credential demo:

```bash
pyxis demo
```

Check provider configuration without printing secrets:

```bash
pyxis doctor
```

Run a provider-backed prompt after configuring `OPENAI_BASE_URL`,
`OPENAI_API_KEY`, and `OPENAI_MODEL`:

```bash
pyxis run "Plan a simple research workflow"
pyxis run "Draft a concise plan" --stream
pyxis run "Plan a simple research workflow" --save-snapshot session-audit.json
pyxis inspect session-audit.json
```

CLI defaults to `.env.local` and `.pyxis-memory.json`. Both are local-first;
`.env.local` should hold real credentials and stay out of git.

## 3-Minute Python Start

```python
from pyxis import Agent, MockProvider, Pyxis

agent = Agent(
    name="navigator",
    instructions="Help the user move through work calmly and clearly.",
    provider=MockProvider(output="Here is a concise plan."),
)

session = Pyxis(agent=agent).session()
result = session.navigate("Plan a controlled research workflow")

print(result.decision)
print(result.output)
```

`Session.navigate()` is the main entry point. It records dialogue, asks the
`Compass` what kind of step is needed, runs the agent when appropriate, and
records observable events.

## Write Your Own Loop

The high-level API is only a convenience. Advanced users can control the turn
step by step:

```python
analysis = session.analyze("Plan a controlled research workflow")
prompt = session.build_agent_prompt(
    "Plan a controlled research workflow",
    analysis,
)

if prompt is not None:
    agent_result = session.run_agent(
        prompt,
        context={"decision": analysis.decision.type.value},
    )
    action = session.parse_action(agent_result.output)
    output, metadata = session.dispatch_action(
        action,
        original_output=agent_result.output,
    )
    result = session.record_agent_response(
        output,
        decision=analysis.decision.type.value,
        metadata=metadata,
    )
```

This keeps Pyxis convenient like a harness, but flexible like a framework: you
can customize prompting, routing, retries, review steps, or UI handoffs without
giving up events, checkpoints, policy, or snapshots.

## Use A Real Provider

Pyxis works with OpenAI-compatible chat completions APIs through standard
environment variables:

```bash
export OPENAI_BASE_URL="https://example.com/v1"
export OPENAI_API_KEY="..."
export OPENAI_MODEL="your-model"
```

```python
import os

from pyxis import Agent, OpenAICompatibleProvider, Pyxis

provider = OpenAICompatibleProvider(
    model=os.environ["OPENAI_MODEL"],
    max_retries=2,
    backoff=0.5,
)

agent = Agent(name="navigator", provider=provider)
session = Pyxis(agent=agent).session()

result = session.navigate("Plan a simple research workflow")
print(result.output)
```

Streaming uses the same session:

```python
for event in session.stream("Draft a concise plan"):
    if event.type == "delta":
        print(event.data["text"], end="")
```

## Get Structured Output

Use `structured_run()` when a workflow needs strict JSON for signals, briefings,
scores, or other application objects:

```python
result = session.structured_run(
    "Score this signal",
    schema={
        "type": "object",
        "required": ["importance", "reason"],
        "properties": {
            "importance": {"type": "number"},
            "reason": {"type": "string"},
        },
    },
    max_retries=1,
)

if result.valid:
    print(result.output["importance"])
else:
    print(result.errors)
```

## Add A Controlled Tool

Tools are normal Python callables with explicit risk and action metadata.
Pyxis validates arguments before executing the function.

```python
from pyxis import Agent, Pyxis, tool

@tool(risk="high", action="file_write")
def write_file(path: str, content: str) -> str:
    """Pretend to write content to a file."""

    return f"would write {len(content)} characters to {path}"

session = Pyxis(agent=Agent(name="navigator", tools=[write_file])).session()
result = session.call_tool("write_file", "notes.txt", content="hello")

if result.requires_confirmation:
    checkpoint = result.checkpoint
    print(checkpoint.summary)
    print(checkpoint.preview)
```

High-risk actions pause by default. The host application can approve, reject,
persist, inspect, or render the checkpoint.

Async tools use the explicit async API:

```python
@tool(risk="low", action="network_fetch")
async def fetch_url(url: str) -> str:
    return f"body:{url}"

result = await session.acall_tool("fetch_url", "https://example.com")
```

## Save And Restore A Session

Snapshots are JSON-safe, versioned, and optionally redacted:

```python
from pyxis import SnapshotRedactionPolicy

policy = SnapshotRedactionPolicy(redact_keys={"api_key", "customer_email"})
session.save_snapshot("session-audit.json", redact=True, redaction_policy=policy)
```

Restore is explicit. Snapshots never import arbitrary Python code:

```python
from pyxis import SnapshotRestoreCatalog, load_snapshot, restore_session

snapshot = load_snapshot("session-audit.json")
restored = restore_session(
    snapshot,
    catalog=SnapshotRestoreCatalog(tools={"write_file": write_file}),
)
```

Pending tool calls and workflows can resume after their callables are registered
by name.

## Observe What Happened

Every session has an append-only event log:

```python
for event in session.events:
    print(event.type, event.payload)
```

Use `EVENT_SCHEMAS` when building a UI, audit exporter, or test harness that
needs stable payload contracts.

Applications can attach event sinks when they need to persist or forward events:

```python
from pyxis import EventLog, InMemoryEventSink, Session

sink = InMemoryEventSink()
session = Session(agent=agent, events=EventLog(sinks=[sink]))
```

## CLI Cheat Sheet

```bash
pyxis demo
pyxis doctor
pyxis run "Plan a simple research workflow"
pyxis run "Draft a concise plan" --stream
pyxis run "..." --approve
pyxis inspect session-audit.json
pyxis memory show
pyxis memory clear
pyxis workflow demo
```

## Examples

```bash
PYTHONPATH=src python3 examples/pi_like_guided_planning.py
PYTHONPATH=src python3 examples/basic_openai_compatible.py
PYTHONPATH=src python3 examples/agent_tool_call.py
```

`examples/pi_like_guided_planning.py` does not need provider credentials. The
OpenAI-compatible examples read `.env.local`; that file is ignored by git.

## Documentation

Start here:

- [API Reference](API_REFERENCE.md): stable public API and compatibility policy.
- [Cookbook](docs/guides/cookbook.md): small composable usage patterns.
- [Control Flow Guide](docs/guides/control-flow.md): use the default
  `navigate()` path or write your own loop.
- [Structured Output](docs/guides/structured-output.md): parse and validate
  provider JSON with lightweight schemas.
- [Async](docs/guides/async.md): async tools, providers, workflows, and resume.
- [Scheduling](docs/guides/scheduling.md): call Pyxis from cron, workers, or
  application schedulers without adding scheduling to core.
- [Tool Authoring Guide](docs/guides/tool-authoring.md): tools, validation,
  policy, and restore expectations.
- [Provider Guide](docs/guides/provider-guide.md): provider contracts,
  streaming, timeout, cancellation, and errors.
- [Safety And Control](docs/guides/safety-control.md): policy modes, deny
  lists, risk overrides, and checkpoint options.
- [Migration Guide](docs/guides/migration.md): moving early MVP code to the 1.0
  contract.

Concept docs:

- [Session](docs/concepts/session.md)
- [Checkpoint](docs/concepts/checkpoint.md)
- [Tool Actions](docs/concepts/tool-actions.md)
- [Workflows](docs/concepts/workflows.md)
- [Providers](docs/concepts/providers.md)
- [Events](docs/concepts/events.md)
- [Memory](docs/concepts/memory.md)

Chinese entry point:

- [README.zh-CN.md](README.zh-CN.md)

## Design Principles

Pyxis stays small at the center:

- no hidden autonomous loop
- no required vector database
- no forced web framework
- no provider-specific logic in session orchestration

The core job is to make agent work navigable: visible decisions, controlled
actions, resumable state, and enough structure for people to stay oriented.

## Status

Pyxis `1.x` is the stable contract for the core harness: public API, controlled
tools, restorable snapshots, provider streaming, policy/consent semantics,
event observability, CLI workflows, and synchronized documentation.
