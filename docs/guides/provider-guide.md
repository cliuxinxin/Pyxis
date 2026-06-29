# Provider Guide

Providers connect Pyxis to model backends while keeping session orchestration
provider-neutral.

## Required Contract

A provider implements:

```python
from pyxis import CompletionRequest, CompletionResult

class MyProvider:
    def complete(self, request: CompletionRequest) -> CompletionResult:
        ...
```

`CompletionRequest` contains:

- `prompt`
- `instructions`
- `context`
- `timeout`
- `cancellation_token`

`CompletionResult` should include:

- `output`
- `raw`
- `metadata`
- `usage`
- `finish_reason`

## Optional Streaming

Providers can support native streaming:

```python
from pyxis import CompletionChunk

class MyProvider:
    def stream(self, request):
        yield CompletionChunk(text="hel")
        yield CompletionChunk(text="lo", finish_reason="stop")
```

`Session.stream()` emits `delta` events for chunks with text and records
provider lifecycle events in the session event log.

## Errors

Providers should raise:

- `ProviderConfigurationError` for missing configuration.
- `ProviderRequestError` for request or response failures.
- `ProviderTimeoutError` for timeouts.
- `ProviderCancelledError` for cancellation.

## Timeout And Cancellation

Check cancellation before network work and between streaming chunks:

```python
if request.cancellation_token is not None:
    request.cancellation_token.throw_if_cancelled()
```

Use `request.timeout` when provided. Otherwise use the provider's configured
default timeout.

## OpenAI-Compatible Provider

`OpenAICompatibleProvider` reads:

- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

It supports completion, SSE streaming, usage extraction, finish reasons,
timeouts, cancellation, and retry/backoff before a streaming response opens.
