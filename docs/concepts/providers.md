# Providers

Providers connect Pyxis to model backends.

The stable provider contract has two layers:

- `complete(request) -> CompletionResult`
- optional `stream(request) -> Iterator[CompletionChunk]`

## Completion Request

`CompletionRequest` contains:

- `prompt`: user-facing task prompt.
- `instructions`: system-style instructions assembled by the agent.
- `context`: provider-neutral metadata.
- `timeout`: optional per-request timeout override.
- `cancellation_token`: optional `CancellationToken`.

Providers should check cancellation before starting network work and while
streaming.

## Completion Result

`CompletionResult` contains:

- `output`: final model text.
- `raw`: provider-native response.
- `metadata`: provider-neutral metadata for callers that need it.
- `usage`: token usage when the provider returns it.
- `finish_reason`: final stop reason when the provider returns it.

## Streaming

Provider-native streaming yields `CompletionChunk` objects:

- `text`: token or text delta. It may be empty on final metadata chunks.
- `raw`: provider-native chunk.
- `metadata`: provider-neutral metadata.
- `usage`: optional usage data.
- `finish_reason`: optional stop reason.

OpenAI-compatible providers commonly emit a final chunk with empty text and a
`finish_reason`. Pyxis treats that as a valid chunk, not an error.

## Errors

Providers should raise:

- `ProviderConfigurationError` for missing local setup, such as a missing API key.
- `ProviderRequestError` for failed requests or invalid responses.
- `ProviderTimeoutError` for request or stream timeouts.
- `ProviderCancelledError` when a cancellation token is cancelled.

## OpenAI-Compatible Provider

`OpenAICompatibleProvider` uses standard environment variables:

```bash
export OPENAI_BASE_URL="https://example.com/v1"
export OPENAI_API_KEY="..."
export OPENAI_MODEL="model-name"
```

It supports non-streaming chat completions, provider-native SSE streaming,
server-error retries for non-streaming requests, per-request timeout overrides,
usage metadata, finish reasons, and cancellation tokens.
