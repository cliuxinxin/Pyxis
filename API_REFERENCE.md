# Pyxis API Reference

This document tracks the public API surface Pyxis intends to stabilize for 1.0.

Pyxis is currently `0.x`, so small adjustments are still possible. The 1.0
contract will freeze the classes, functions, and behavior documented here.

## Compatibility Policy

After 1.0:

- Public names exported from `pyxis` remain backward compatible within the same
  major version.
- New optional parameters may be added without a major version bump.
- Behavior that changes safety, checkpointing, validation, or persistence
  semantics requires a changelog entry and migration note.
- Deprecated APIs stay available for at least one minor release before removal.
- Private helpers, underscored methods, and undocumented module internals are not
  covered by the compatibility guarantee.

Before 1.0:

- Breaking changes should be rare, intentional, and documented in
  `CHANGELOG.md`.
- Each breaking change should include a migration path.

## Core Objects

### `Agent`

Role-bound execution body with provider, tools, memory, and response style.

Stable surface:

- `Agent(name, instructions="", provider=..., tools=..., memory=..., response_style=...)`
- `run(prompt, *, context=None) -> AgentResult`
- `stream(prompt, *, context=None) -> Iterator[CompletionChunk]`
- `completion_request(prompt, *, context=None) -> CompletionRequest`
- `get_tool(name) -> Tool | None`
- `tool_manifest() -> list[dict]`
- `system_instructions() -> str`

### `Session`

Human-agent working context.

Stable surface:

- `navigate(user_input, *, requires_confirmation=False) -> NavigationResult`
- `stream(user_input, *, requires_confirmation=False) -> Iterator[StreamEvent]`
- `call_tool(name, *args, **kwargs) -> ToolResult`
- `checkpoint(...) -> Checkpoint`
- `approve_checkpoint(checkpoint_id) -> Checkpoint`
- `reject_checkpoint(checkpoint_id) -> Checkpoint`
- `resume_checkpoint(checkpoint_id) -> ToolResult`
- `run(workflow, value) -> WorkflowResult`
- `resume_workflow(checkpoint_id) -> WorkflowResult`
- `snapshot(*, redact=False) -> dict`
- `save_snapshot(path, *, redact=False) -> Path`

### Snapshot Restore

Snapshots can be restored through an explicit callable catalog.

Stable surface:

- `SnapshotRestoreCatalog(tools=..., workflows=..., provider=None, memory=None, instructions="")`
- `SnapshotRestoreCatalog.register_tool(tool) -> SnapshotRestoreCatalog`
- `SnapshotRestoreCatalog.register_workflow(workflow) -> SnapshotRestoreCatalog`
- `restore_session(snapshot, *, catalog=None) -> Session`

Pyxis does not import arbitrary callables from a snapshot. Tools and workflows
must be registered by name. Missing registrations raise `SnapshotRestoreError`.

### `Tool`

Callable capability exposed to agents.

Stable surface:

- `@tool(...)`
- `Tool.manifest() -> dict`
- `Tool.parameter_schema() -> dict`
- `Tool.validate_arguments(*args, **kwargs) -> None`
- `Tool.__call__(*args, **kwargs) -> ToolResult`

Tool calls are validated before execution. Validation covers callable binding,
required parameters, unexpected parameters, defaults, and common annotation
types. Invalid calls raise `ToolValidationError`.

### `Workflow`

Observable workflow sequence.

Stable surface:

- `step(name, fn) -> Workflow`
- `checkpoint(reason, *, name=None) -> Workflow`
- `ask(prompt, *, name=None) -> Workflow`
- `reflect(prompt, *, name=None) -> Workflow`
- `revise(prompt, *, name=None) -> Workflow`
- `run(value, *, start_at=0, completed=None) -> WorkflowResult`

### `Checkpoint`

Human consent object.

Stable fields:

- `id`
- `reason`
- `action`
- `payload`
- `summary`
- `risk_reason`
- `preview`
- `options`
- `status`

Stable methods:

- `approve()`
- `reject()`
- `approved`
- `to_dict()`

### `Memory`

Minimal memory protocol and bounded session memory.

Stable surface:

- `Memory.get(key, default=None)`
- `Memory.set(key, value)`
- `Memory.to_dict()`
- `SessionMemory.set_preference(key, value)`
- `SessionMemory.get_preference(key, default=None)`
- `SessionMemory.clear_preferences(key=None)`
- `SessionMemory.set_project_context(...)`
- `SessionMemory.clear_project_context()`
- `SessionMemory.clear(key=None)`

### `Provider`

Provider protocol for model backends.

Stable surface:

- `complete(request: CompletionRequest) -> CompletionResult`
- Optional `stream(request: CompletionRequest) -> Iterator[CompletionChunk]`

`CompletionRequest`, `CompletionResult`, and `CompletionChunk` are public data
objects. Providers should raise `ProviderConfigurationError` for missing local
configuration and `ProviderRequestError` for request or response failures.

## Public Exceptions

- `ToolValidationError`: tool arguments do not match the tool signature.
- `ToolExecutionError`: user tool code raised during execution.
- `ToolNotFound`: requested tool is not registered on the agent.
- `CheckpointNotFound`, `CheckpointNotApproved`, `CheckpointRejected`.
- `ProviderConfigurationError`, `ProviderRequestError`.
- `SnapshotRestoreError`: a snapshot cannot be restored with the provided
  catalog.

## Deprecation Process

1. Add a changelog entry and migration note.
2. Keep the old API available for at least one minor release.
3. Emit a warning when practical.
4. Remove only in the next major version, or before 1.0 with explicit release
   notes.
