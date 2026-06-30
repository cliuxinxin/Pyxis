# Async Tools And Workflows

Use async APIs when a host application performs IO-heavy work such as fetching
web pages, RSS feeds, GitHub data, email, or internal services.

Pyxis keeps sync and async execution explicit:

- sync APIs execute sync callables;
- async APIs execute sync or async callables;
- sync APIs reject async callables with a clear error.

Pyxis does not call `asyncio.run()` inside sync APIs. This keeps it safe to use
inside web servers, notebooks, workers, and applications that already own an
event loop.

## Async Tools

```python
from pyxis import Agent, Pyxis, tool

@tool(risk="low", action="network_fetch")
async def fetch_url(url: str) -> str:
    return f"body:{url}"

session = Pyxis(agent=Agent(name="collector", tools=[fetch_url])).session()
result = await session.acall_tool("fetch_url", "https://example.com")

print(result.output)
```

High-risk async tools use the same checkpoint flow:

```python
paused = await session.acall_tool("fetch_url", "https://example.com")

if paused.requires_confirmation:
    session.approve_checkpoint(paused.checkpoint.id)
    result = await session.aresume_checkpoint(paused.checkpoint.id)
```

## Async Workflows

```python
from pyxis import Workflow

async def fetch(signal: str) -> str:
    return f"{signal}:fetched"

workflow = (
    Workflow("collect")
    .step("fetch", fetch)
    .step("parse", lambda value: value.upper())
)

result = await session.arun(workflow, "signal")
print(result.output)
```

Checkpointed workflows can resume asynchronously:

```python
paused = await session.arun(workflow, "signal")

if paused.paused:
    session.approve_checkpoint(paused.checkpoint.id)
    result = await session.aresume_workflow(paused.checkpoint.id)
```

## Async Providers

Providers may implement `acomplete(request)` for async model calls:

```python
from pyxis import CompletionResult

class MyProvider:
    async def acomplete(self, request):
        return CompletionResult(output="hello")
```

`Agent.arun()` and `Session.arun_agent()` use `acomplete()` when available. If a
provider only implements sync `complete()`, async agent execution falls back to
that sync method.
