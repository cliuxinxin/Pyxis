# Migration Guide

Pyxis is still pre-1.0, so this guide tracks the compatibility expectations for
moving from the early MVP line toward the 1.0 contract.

## Environment Variables

Use the common OpenAI-compatible variable names:

- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

Older local custom names should be migrated to these names before publishing
examples, docs, or CI.

## Tool Calls

Tool calls are now validated before execution. Invalid required arguments,
unexpected parameters, duplicate arguments, and common annotation mismatches
raise `ToolValidationError`.

Migration steps:

- Add type annotations for user-facing tool parameters.
- Prefer keyword-object tool calls in model output:
  `{"type":"tool_call","tool":"name","args":{"key":"value"}}`.
- Handle `ToolValidationError` near host UI boundaries when showing model
  mistakes to users.

## Snapshots

Snapshots now include:

- `metadata.kind`
- `metadata.schema_version`
- `events[*].schema_version`

Legacy snapshots without `metadata` restore as schema version 1. Future schema
versions fail clearly with `SnapshotRestoreError` instead of restoring
incorrectly.

Restore now requires an explicit `SnapshotRestoreCatalog` for pending tools and
workflows. Register callable objects by name before calling `restore_session()`.

## Policy

Use `ControlPolicy.safe_default()` unless the host application has a clearer
policy. For stricter applications:

- Use `ControlPolicy.strict()` to require confirmation by default.
- Use `deny_actions` for actions that must never run.
- Use `risk_overrides` for application-specific risk.
- Use `checkpoint_options` when a UI exposes choices beyond approve/reject.

## Events

Session events have a stable schema catalog through `EVENT_SCHEMAS`.

If you were matching raw event names, keep those names. If you are building new
code, prefer `EventType` constants and validate against `EVENT_SCHEMAS`.

## CLI

The CLI now includes:

- `pyxis run --stream`
- `pyxis inspect snapshot.json`
- `pyxis memory show`
- `pyxis memory clear`
- `pyxis workflow demo`

Use `--env-file` and `--memory-file` for local test isolation.
