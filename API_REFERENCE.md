# Pyxis API Reference

This document tracks the public API surface Pyxis stabilizes for the 1.0
contract. The classes, functions, and behavior documented here are the
backward-compatible surface for the 1.x release line.

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

## Core Objects

### `Pyxis`

Small factory object that owns an `Agent`, `Compass`, and `ControlPolicy`.

Stable surface:

- `Pyxis(agent, compass=..., policy=...)`
- `session() -> Session`
- `navigate(user_input, *, requires_confirmation=False) -> NavigationResult`

### `Compass`

Dialogue navigation layer that decides whether to clarify, plan, act, confirm,
or stop.

Stable surface:

- `analyze(user_input, *, requires_confirmation=False) -> CompassAnalysis`
- `CompassAnalysis.intent`
- `CompassAnalysis.goal`
- `CompassAnalysis.clarification`
- `CompassAnalysis.constraints`
- `CompassAnalysis.preferences`
- `CompassAnalysis.decision`

### `Agent`

Role-bound execution body with provider, tools, memory, and response style.

Stable surface:

- `Agent(name, instructions="", provider=..., tools=..., memory=..., response_style=...)`
- `run(prompt, *, context=None, timeout=None, cancellation_token=None) -> AgentResult`
- `arun(prompt, *, context=None, timeout=None, cancellation_token=None) -> AgentResult`
- `stream(prompt, *, context=None, timeout=None, cancellation_token=None) -> Iterator[CompletionChunk]`
- `completion_request(prompt, *, context=None, timeout=None, cancellation_token=None) -> CompletionRequest`
- `get_tool(name) -> Tool | None`
- `tool_manifest() -> list[dict]`
- `system_instructions() -> str`

### `Session`

Human-agent working context.

Stable surface:

- `navigate(user_input, *, requires_confirmation=False) -> NavigationResult`
- `stream(user_input, *, requires_confirmation=False) -> Iterator[StreamEvent]`
- `analyze(user_input, *, requires_confirmation=False) -> CompassAnalysis`
- `build_agent_prompt(user_input, analysis) -> str | None`
- `run_agent(prompt, *, context=None) -> AgentResult`
- `arun_agent(prompt, *, context=None) -> AgentResult`
- `structured_run(prompt, *, schema, max_retries=0, context=None) -> StructuredResult`
- `parse_action(output) -> AgentAction`
- `dispatch_action(action, *, original_output="") -> tuple[str, dict]`
- `record_agent_response(output, *, decision, metadata=None) -> NavigationResult`
- `call_tool(name, *args, **kwargs) -> ToolResult`
- `acall_tool(name, *args, **kwargs) -> ToolResult`
- `checkpoint(...) -> Checkpoint`
- `approve_checkpoint(checkpoint_id) -> Checkpoint`
- `reject_checkpoint(checkpoint_id) -> Checkpoint`
- `resume_checkpoint(checkpoint_id) -> ToolResult`
- `aresume_checkpoint(checkpoint_id) -> ToolResult`
- `run(workflow, value) -> WorkflowResult`
- `arun(workflow, value) -> WorkflowResult`
- `resume_workflow(checkpoint_id) -> WorkflowResult`
- `aresume_workflow(checkpoint_id) -> WorkflowResult`
- `snapshot(*, redact=False, redaction_policy=None) -> dict`
- `save_snapshot(path, *, redact=False, redaction_policy=None) -> Path`

### Snapshot Restore

Snapshots can be restored through an explicit callable catalog.

Stable surface:

- `SnapshotMetadata(kind="pyxis.session", schema_version=1)`
- `SnapshotRedactionPolicy(redact_keys=..., replacement="[REDACTED]")`
- `SnapshotRestoreCatalog(tools=..., workflows=..., provider=None, memory=None, instructions="")`
- `SnapshotRestoreCatalog.register_tool(tool) -> SnapshotRestoreCatalog`
- `SnapshotRestoreCatalog.register_workflow(workflow) -> SnapshotRestoreCatalog`
- `snapshot_metadata(snapshot) -> SnapshotMetadata`
- `restore_session(snapshot, *, catalog=None) -> Session`

Pyxis does not import arbitrary callables from a snapshot. Tools and workflows
must be registered by name. Missing registrations raise `SnapshotRestoreError`.
Snapshots include version metadata so future formats can fail clearly instead
of restoring incorrectly. Redaction policies can customize which snapshot keys
are replaced before export.

### `Tool`

Callable capability exposed to agents.

Stable surface:

- `@tool(...)`
- `Tool.manifest() -> dict`
- `Tool.parameter_schema() -> dict`
- `Tool.validate_arguments(*args, **kwargs) -> None`
- `Tool.is_async -> bool`
- `Tool.__call__(*args, **kwargs) -> ToolResult`
- `Tool.acall(*args, **kwargs) -> ToolResult`

Tool calls are validated before execution. Validation covers callable binding,
required parameters, unexpected parameters, defaults, and common annotation
types. Invalid calls raise `ToolValidationError`.
Synchronous tool execution rejects async tools with a clear error; use
`Tool.acall()` or `Session.acall_tool()` for `async def` tools.

### `Workflow`

Observable workflow sequence.

Stable surface:

- `step(name, fn) -> Workflow`
- `checkpoint(reason, *, name=None) -> Workflow`
- `ask(prompt, *, name=None) -> Workflow`
- `reflect(prompt, *, name=None) -> Workflow`
- `revise(prompt, *, name=None) -> Workflow`
- `run(value, *, start_at=0, completed=None) -> WorkflowResult`
- `arun(value, *, start_at=0, completed=None) -> WorkflowResult`

Synchronous workflow runners reject async steps. Use `Workflow.arun()` or
`Session.arun()` for workflows containing `async def` steps or steps that return
awaitables.

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

### `ControlPolicy`

Human approval policy for actions.

Stable surface:

- `ControlPolicy.safe_default() -> ControlPolicy`
- `ControlPolicy.strict() -> ControlPolicy`
- `ControlPolicy.permissive() -> ControlPolicy`
- `decide(action=..., risk=...) -> PolicyDecision`
- `requires_confirmation(action=..., risk=...) -> bool`

Stable fields:

- `approval_mode`: `permissive`, `balanced`, or `strict`.
- `require_confirmation_for_risk`
- `require_confirmation_for_actions`
- `allow_auto_for_actions`
- `deny_actions`
- `risk_overrides`
- `checkpoint_options`

`deny_actions` wins over automatic allow rules. `risk_overrides` changes the
effective risk used by the policy decision. `checkpoint_options` are copied into
created checkpoints.

### `Event`

Observable session event.

Stable surface:

- `Event(type, payload=..., id=..., created_at=..., schema_version=...)`
- `Event.to_dict() -> dict`
- `EventSink.write(event) -> None`
- `NullEventSink.write(event) -> None`
- `InMemoryEventSink.write(event) -> None`
- `InMemoryEventSink.all() -> list[Event]`
- `InMemoryEventSink.to_list() -> list[dict]`
- `EventLog(sinks=None)`
- `EventLog.emit(event_type, **payload) -> Event`
- `EventLog.append(event, *, notify=False) -> None`
- `EventLog.all() -> list[Event]`
- `EventLog.to_list() -> list[dict]`
- `EventType`
- `EventSchema`
- `EVENT_SCHEMAS`
- `EVENT_SCHEMA_VERSION`

Known Pyxis events validate required payload keys through `EventLog.emit()`.
Unknown event names are allowed for host application events. Stable event
families cover provider, tool, checkpoint, policy, workflow, dialogue, and
snapshot restore behavior. Event sinks let host applications persist or forward
newly emitted events without replacing the in-memory log.

### `StructuredResult`

Structured output result returned by `Session.structured_run()`.

Stable fields:

- `output`
- `raw_output`
- `valid`
- `errors`
- `metadata`

`structured_run()` uses the provider through the normal agent path, parses the
response as JSON, validates a lightweight schema subset, and optionally retries
with validation errors. The first supported schema subset includes `type`,
`required`, `properties`, `items`, and `enum`.

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
- `SessionMemory(store=...)`
- `MemoryItem(namespace, key, value, metadata=..., created_at=..., updated_at=...)`
- `MemoryItem.to_dict() -> dict`
- `MemoryStore.get(namespace, key, default=None)`
- `MemoryStore.set(namespace, key, value, *, metadata=None)`
- `MemoryStore.delete(namespace, key)`
- `MemoryStore.list(namespace) -> list[MemoryItem]`
- `MemoryStore.to_dict() -> dict`
- `NoMemoryStore`
- `InMemoryStore(items=None)`

`SessionMemory` remains the bounded session-local memory layer. `MemoryStore`
is the long-term adapter protocol for host applications that want durable
preferences, feedback, watchlists, or other product memory. Core Pyxis does not
ship a database-backed adapter.

### `Provider`

Provider protocol for model backends.

Stable surface:

- `complete(request: CompletionRequest) -> CompletionResult`
- Optional `acomplete(request: CompletionRequest) -> CompletionResult`
- Optional `stream(request: CompletionRequest) -> Iterator[CompletionChunk]`

`CompletionRequest`, `CompletionResult`, and `CompletionChunk` are public data
objects. `CompletionRequest` includes `timeout` and `cancellation_token`.
`CompletionResult` and `CompletionChunk` include `usage` and `finish_reason`.

Providers should raise `ProviderConfigurationError` for missing local
configuration, `ProviderRequestError` for request or response failures,
`ProviderTimeoutError` for timeouts, and `ProviderCancelledError` for cancelled
requests.

## Public Exceptions

- `ToolValidationError`: tool arguments do not match the tool signature.
- `ToolExecutionError`: user tool code raised during execution.
- `ToolNotFound`: requested tool is not registered on the agent.
- `PolicyDeniedError`: a control policy denied an action before execution.
- `CheckpointNotFound`, `CheckpointNotApproved`, `CheckpointRejected`.
- `ProviderConfigurationError`, `ProviderRequestError`, `ProviderTimeoutError`,
  `ProviderCancelledError`.
- `EventSinkError`: an event sink failed to write an emitted event.
- `SnapshotRestoreError`: a snapshot cannot be restored with the provided
  catalog.

## Deprecation Process

1. Add a changelog entry and migration note.
2. Keep the old API available for at least one minor release.
3. Emit a warning when practical.
4. Remove only in the next major version, or before 1.0 with explicit release
   notes.
