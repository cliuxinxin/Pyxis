# Pyxis

A minimal, human-centered Python agent harness for building controllable AI
workflows.

Pyxis is named after the mariner's compass constellation. It is designed around
orientation, navigation, and deliberate movement: not just making an agent act,
but helping people and agents move through work together with clarity and
control.

## Why Pyxis

Most agent frameworks begin with automation. Pyxis begins with guidance.

Its core idea is simple:

> The conversation is the control surface, and the human stays in the loop.

Pyxis is inspired by the human-centered feel of personal AI systems, but it is
not a companion chatbot. It translates that spirit into a Python harness for
developers who want workflows that are calm, observable, interruptible, and
extensible.

## Core Concepts

- `Session`: a shared working context between a human and an agent.
- `Dialogue`: semantic conversation state, not only raw messages.
- `Compass`: the navigation layer that decides whether to ask, plan, act,
  confirm, or stop.
- `Intent`, `UserGoal`, and `Clarification`: structured readings of what the
  user wants before the agent acts.
- `ResponseStyle`: lightweight response shaping for calm, concise, supportive
  output.
- `SessionMemory`: bounded, inspectable memory for preferences and project
  context.
- `Checkpoint`: a human confirmation point before sensitive actions.
- `ControlPolicy`: rules for what can run automatically and what needs review.
- `Agent`: the role-bound execution body.
- `Tool`: a Python callable exposed as an agent capability.
- `Workflow`: a simple, observable sequence of steps.
- `Provider`: a model backend interface.

## Current Capabilities

- OpenAI-compatible provider using standard `OPENAI_*` environment variables.
- Agent JSON action protocol for model-requested tool calls.
- Automatic tool manifest injection.
- Checkpointed tool execution for high-risk actions.
- Pausable workflows with approve, reject, and resume flows.
- JSON-safe session snapshots and snapshot file persistence.
- Minimal CLI for configuration checks and one-off runs.
- Structured dialogue analysis that favors clarification before action when a
  request is underspecified.
- Bounded in-process memory for user preferences, project context, and
  temporary scratchpad state.

## Install

Pyxis is currently a local package scaffold.

```bash
pip install -e ".[dev]"
```

## Quick Start

```python
from pyxis import Agent, MockProvider, Pyxis

agent = Agent(
    name="navigator",
    instructions="Help the user move through work calmly and clearly.",
    provider=MockProvider(output="Here is a concise plan."),
)

px = Pyxis(agent=agent)
result = px.navigate("Plan a simple research workflow")

print(result.output)
```

## CLI

Pyxis includes a small CLI for local checks and one-off runs:

```bash
pyxis doctor
```

`doctor` checks `OPENAI_BASE_URL`, `OPENAI_API_KEY`, and `OPENAI_MODEL` without
printing secret values.

Run a prompt with the configured provider:

```bash
pyxis run "Plan a simple research workflow"
```

Save an audit snapshot while running:

```bash
pyxis run "Plan a simple research workflow" --save-snapshot session-audit.json
```

Approve a checkpoint produced by a run:

```bash
pyxis run "..." --approve
```

When approval is not automatic, the CLI shows a consent-oriented prompt:

```text
Pyxis wants to run a high-risk action.

Action: file_write
Reason: This may modify local files.
Preview: notes.txt

Approve? [y/N]
```

## Session Snapshots

Sessions expose a JSON-safe snapshot for inspection and audit trails:

```python
snapshot = session.snapshot()

print(snapshot["dialogue"])
print(snapshot["events"])
print(snapshot["checkpoints"])
```

Snapshots include dialogue, events, checkpoints, pending tool calls, and pending
workflows. They are intended for inspection first; full persistence and
callable restoration can be layered on later.

You can also save and load audit snapshots:

```python
from pyxis import load_snapshot

session.save_snapshot("session-audit.json")
snapshot = load_snapshot("session-audit.json")
```

Use redaction when exporting snapshots that may contain sensitive payloads:

```python
session.save_snapshot("session-audit.json", redact=True)
```

## Memory With Boundaries

Pyxis keeps memory explicit and inspectable. It does not require a vector
database or persist sensitive content by default.

```python
from pyxis import Agent, Pyxis, SessionMemory

memory = SessionMemory()
memory.set_preference("tone", "concise")
memory.set_preference("approval_mode", "strict")
memory.set_project_context(name="Pyxis", description="Python agent harness")

session = Pyxis(agent=Agent(name="navigator", memory=memory)).session()

print(memory.to_dict())
memory.clear_preferences("tone")
memory.clear_project_context()
```

Snapshots include bounded memory so users can inspect what Pyxis is carrying
forward. Redacted snapshots continue to protect sensitive keys.

## OpenAI-Compatible Providers

Pyxis can call OpenAI-compatible chat completions APIs without requiring an SDK.

Configure credentials through environment variables:

```bash
export OPENAI_BASE_URL="https://ark.cn-beijing.volces.com/api/coding/v3"
export OPENAI_API_KEY="..."
export OPENAI_MODEL="your-model"
```

Then use `OpenAICompatibleProvider`:

```python
import os

from pyxis import Agent, OpenAICompatibleProvider, Pyxis

provider = OpenAICompatibleProvider(
    model=os.environ["OPENAI_MODEL"],
    max_retries=2,
    backoff=0.5,
)

agent = Agent(
    name="navigator",
    instructions="Help the user move through work calmly and clearly.",
    provider=provider,
)

result = Pyxis(agent=agent).navigate("Plan a simple research workflow")
print(result.output)
```

You can also pass `base_url` and `api_key` directly when embedding Pyxis in
another application. Avoid committing real keys to the repository.
Provider responses include any returned `usage` metadata when available.

### Live Smoke Test

Create a local env file from the example:

```bash
cp .env.example .env.local
```

Fill in `OPENAI_API_KEY` and `OPENAI_MODEL` in `.env.local`. The file is ignored
by git.

Then run:

```bash
PYTHONPATH=src python3 examples/basic_openai_compatible.py
```

The example reads `.env.local`, calls the configured OpenAI-compatible provider,
and prints the agent response.

To test whether a live model follows Pyxis tool-call JSON, run:

```bash
PYTHONPATH=src python3 examples/agent_tool_call.py
```

This example exposes one low-risk tool and one high-risk tool. The low-risk tool
should execute directly. The high-risk tool should pause with a checkpoint.

## Session First

Pyxis favors `Session.navigate()` over a bare `Agent.run()` call.

```python
from pyxis import Agent, Pyxis

session = Pyxis(agent=Agent(name="navigator")).session()

result = session.navigate("帮我规划一个竞品研究流程")
print(result.decision)
print(result.output)
```

The `Compass` chooses the next move. A request might become a plan, a direct
agent response, a clarification question, or a checkpoint.

Each turn also records a structured reading of the conversation:

```python
result = session.navigate("帮我弄一下")

print(session.dialogue.intent)
print(session.dialogue.clarifications)
print(result.metadata["analysis"].to_dict())
```

Pyxis treats vague requests as a chance to clarify the desired outcome before
acting, while specific requests continue through the agent or planning path.

Sessions can also expose high-level stream events:

```python
for event in session.stream("帮我规划一个竞品研究流程"):
    if event.type == "delta":
        print(event.data["text"], end="")
    elif event.type == "done":
        print()
```

When the provider supports native streaming, Pyxis yields `delta` events before
the final `result` and `done` events. Providers without streaming support still
use the turn-level `start`, `result`, and `done` events.

## Tools

```python
from pyxis import Agent, tool

@tool(risk="medium", action="summarize")
def summarize(text: str) -> str:
    """Summarize text."""
    return text[:120]

agent = Agent(
    name="research-guide",
    tools=[summarize],
)
```

Tools carry risk and action metadata so a `ControlPolicy` can decide whether
human confirmation is needed.

## Controlled Tool Calls

Call tools through `Session` when you want Pyxis to enforce checkpoints.

```python
from pyxis import Agent, Pyxis, tool

@tool(risk="high", action="file_write")
def write_file(path: str, content: str) -> str:
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)
    return path

session = Pyxis(
    agent=Agent(
        name="navigator",
        tools=[write_file],
    )
).session()

result = session.call_tool("write_file", "notes.txt", content="hello")

if result.requires_confirmation:
    checkpoint = result.checkpoint
    session.approve_checkpoint(checkpoint.id)
    result = session.resume_checkpoint(checkpoint.id)

print(result.output)
```

High-risk tools pause before execution. The pending call is resumed only after
the checkpoint is approved.

Checkpoints carry user-facing consent details:

```python
print(checkpoint.summary)
print(checkpoint.risk_reason)
print(checkpoint.preview)
print(checkpoint.options)
```

## Agent Tool-Call Protocol

Agents can request tool calls by returning a small JSON action object:

```json
{
  "type": "tool_call",
  "tool": "summarize",
  "args": {
    "text": "Pyxis helps agents move through work with control."
  }
}
```

`Session.navigate()` parses this protocol after the agent responds. Low-risk
tools run immediately. High-risk tools use the same checkpoint flow as manual
`session.call_tool()` calls.

```python
from pyxis import Agent, MockProvider, Pyxis, tool

@tool(risk="low", action="summarize")
def summarize(text: str) -> str:
    return text[:32]

agent = Agent(
    name="navigator",
    provider=MockProvider(
        output='{"type":"tool_call","tool":"summarize","args":{"text":"Pyxis keeps humans in control."}}'
    ),
    tools=[summarize],
)

result = Pyxis(agent=agent).navigate("Summarize this")
print(result.output)
```

Pyxis can read action JSON directly, from a JSON code block, or from surrounding
explanatory text. If no valid action JSON is found, Pyxis treats the response as
a normal message.

When an agent has tools, Pyxis automatically adds a compact tool manifest and
the action protocol to the provider instructions. Developers define tools once;
the agent receives their name, description, risk, action metadata, and parameter
schema derived from the function signature.

## Workflows

```python
from pyxis import Workflow

workflow = (
    Workflow("research")
    .step("clean", lambda text: text.strip())
    .step("summarize", lambda text: text[:80])
)

result = workflow.run("  Pyxis helps agents navigate work.  ")
print(result.output)
```

Workflows can also pause at human checkpoints when they run through a session:

```python
from pyxis import Agent, Pyxis, Workflow

workflow = (
    Workflow("draft")
    .step("clean", lambda text: text.strip())
    .checkpoint("Review cleaned text before writing the report.")
    .step("report", lambda text: f"Report: {text}")
)

session = Pyxis(agent=Agent(name="navigator")).session()
result = session.run(workflow, "  Pyxis keeps work controllable.  ")

if result.paused:
    checkpoint = result.checkpoint
    session.approve_checkpoint(checkpoint.id)
    result = session.resume_workflow(checkpoint.id)

print(result.output)
```

Reflective workflows can pause to ask, reflect, or revise before continuing:

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

These steps use the same checkpoint/resume flow, but their metadata makes the
pause feel like calibration rather than a mechanical gate.

## Design Direction

Pyxis is intentionally small at the center:

- no required model provider
- no required vector database
- no hidden autonomous loop
- no forced web framework

The first milestone is to make the harness feel clear:

1. navigate through conversation
2. make decisions visible
3. pause before risky actions
4. compose tools and workflows
5. add real providers at the edges

## Status

This repository is an early MVP. The current provider is `MockProvider`, which
keeps the core testable before real model integrations are added.
