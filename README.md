# Pyxis

A minimal, human-centered Python agent harness for building controllable AI
workflows.

Pyxis is named after the mariner's compass constellation. It is designed around
orientation, navigation, and deliberate movement: not just making an agent act,
but helping people and agents move through work together with clarity and
control.

## Why Pyxis

Most agent frameworks begin with automation. Pyxis begins with guidance.

> The conversation is the control surface, and the human stays in the loop.

Pyxis translates the human-centered feel of personal AI systems into a Python
harness for developers who want workflows that are calm, observable,
interruptible, and extensible.

## Current Capabilities

- Human-centered `Session` navigation with structured `Dialogue` state.
- `Compass` analysis for ask, plan, act, confirm, or stop decisions.
- `Intent`, `UserGoal`, `Clarification`, `TonePolicy`, and `ResponseStyle`.
- Consent-oriented `Checkpoint` objects with summary, reason, preview, options,
  approve, reject, and resume flows.
- Bounded `SessionMemory` for user preferences, project context, and scratchpad
  state.
- Tool manifests and JSON action parsing for model-requested tool calls.
- Pausable and reflective workflows with `checkpoint()`, `ask()`, `reflect()`,
  and `revise()`.
- OpenAI-compatible provider support with standard `OPENAI_*` environment
  variables and provider-native streaming.
- JSON-safe snapshots with optional redaction.
- Snapshot restore through explicit tool and workflow catalogs.
- CLI commands for `doctor`, `run`, and local `demo`.

## Install

Pyxis is currently a local package scaffold:

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

result = Pyxis(agent=agent).navigate("Plan a simple research workflow")
print(result.decision)
print(result.output)
```

## CLI

Run a local demo without provider credentials:

```bash
pyxis demo
```

Check provider configuration:

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

## Provider Configuration

Pyxis can call OpenAI-compatible chat completions APIs without requiring an SDK.

```bash
export OPENAI_BASE_URL="https://ark.cn-beijing.volces.com/api/coding/v3"
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
result = Pyxis(agent=agent).navigate("Plan a simple research workflow")
print(result.output)
```

Provider-native streaming is available through `Session.stream()` when the
provider supports it:

```python
for event in session.stream("Draft a concise plan"):
    if event.type == "delta":
        print(event.data["text"], end="")
```

## Core Concepts

- [API Reference](API_REFERENCE.md): public API surface, compatibility policy,
  and deprecation policy.
- [Session](docs/concepts/session.md): shared working context, dialogue,
  events, snapshots, and streaming.
- [Checkpoint](docs/concepts/checkpoint.md): human approval before sensitive
  actions.
- [Tool Actions](docs/concepts/tool-actions.md): tool metadata, risk, action,
  and model-requested tool calls.
- [Workflows](docs/concepts/workflows.md): sequential, checkpointed, and
  reflective workflows.
- [Providers](docs/concepts/providers.md): completion, streaming, usage,
  finish reasons, timeout, and cancellation contract.

## Examples

Local examples:

```bash
PYTHONPATH=src python3 examples/pi_like_guided_planning.py
PYTHONPATH=src python3 examples/basic_openai_compatible.py
PYTHONPATH=src python3 examples/agent_tool_call.py
```

`examples/pi_like_guided_planning.py` does not need provider credentials. The
OpenAI-compatible examples read `.env.local`; that file is ignored by git.

## Design Direction

Pyxis is intentionally small at the center:

- no required model provider
- no required vector database
- no hidden autonomous loop
- no forced web framework

The first milestone is to make the harness feel clear: navigate through
conversation, make decisions visible, pause before risky actions, compose tools
and workflows, and add real providers at the edges.

## Status

This repository is an early alpha. `0.1.1` is the next release line after the
initial `0.1.0` MVP, focused on human-centered dialogue, consent UX, bounded
memory, reflective workflows, provider-native streaming, and cleaner docs.
