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
- `Checkpoint`: a human confirmation point before sensitive actions.
- `ControlPolicy`: rules for what can run automatically and what needs review.
- `Agent`: the role-bound execution body.
- `Tool`: a Python callable exposed as an agent capability.
- `Workflow`: a simple, observable sequence of steps.
- `Provider`: a model backend interface.

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
