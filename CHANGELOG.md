# Changelog

All notable changes to Pyxis will be documented in this file.

## 1.0.1 - 2026-06-30

Runtime extensibility release for product integrations such as Astra.

### Added

- Event sinks through `EventSink`, `NullEventSink`, `InMemoryEventSink`, and
  `EventSinkError` so host applications can persist or forward emitted events.
- `Session.structured_run()` and `StructuredResult` for lightweight
  schema-constrained JSON outputs with local validation and retry.
- Structured output events:
  `StructuredOutputRequested`, `StructuredOutputParsed`, and
  `StructuredOutputValidationFailed`.
- Async execution primitives for IO-heavy applications:
  `Agent.arun()`, `Session.arun_agent()`, `Session.acall_tool()`,
  `Session.aresume_checkpoint()`, `Session.arun()`, and
  `Session.aresume_workflow()`.
- Async tool support through `Tool.is_async` and `Tool.acall()`.
- Async workflow support through `Workflow.arun()`.
- Long-term memory protocol through `MemoryStore`, `MemoryItem`,
  `NoMemoryStore`, and `InMemoryStore`.
- Optional `SessionMemory(store=...)` snapshots for attached long-term memory
  stores.
- Guides for async execution, structured output, memory stores, and scheduling
  boundaries.

### Changed

- `EventLog` now accepts optional sinks and supports
  `append(event, notify=False)` to avoid re-sending restored historical events
  by default.
- Synchronous tool and workflow runners now reject async callables with clear
  errors instead of implicitly owning an event loop.

## 1.0.0 - 2026-06-29

Stability release for the public Pyxis agent harness contract.

### Added

- Initial `API_REFERENCE.md` with public API surface, compatibility policy, and
  deprecation process.
- Snapshot restore with `SnapshotRestoreCatalog` and `restore_session()` for
  registered tools and workflows.
- Provider contract fields for `usage`, `finish_reason`, request timeout, and
  cancellation.
- Policy decisions with approval modes, action deny lists, risk overrides, and
  checkpoint options.
- Stable event schemas with provider lifecycle, workflow step, checkpoint,
  policy, and session restore observability.
- CLI commands for snapshot inspection, local memory show/clear, streaming runs,
  and workflow demos.
- Snapshot metadata schema versioning and customizable redaction policies.
- Cookbook, migration, provider, and tool authoring guides for 1.0 readiness.
- OpenAI-compatible stream retries before response open, with no replay after
  stream deltas may have been emitted.
- Programmable session control primitives for writing custom agent turn loops.
- Tool argument validation for required parameters, unexpected parameters,
  defaults, common annotations, and `typing.Literal`.
- Public `ToolValidationError` for invalid tool calls.

## 0.1.1 - 2026-06-29

Human-centered refinement release.

### Added

- Structured dialogue analysis with `Intent`, `UserGoal`, `Clarification`,
  `TonePolicy`, and `ResponseStyle`.
- Consent-oriented checkpoint fields: `summary`, `risk_reason`, `preview`, and
  `options`.
- Bounded in-process `SessionMemory`, `UserPreferences`, and `ProjectContext`.
- Reflective workflow steps: `ask()`, `reflect()`, and `revise()`.
- Provider-native streaming for OpenAI-compatible providers.
- `pyxis demo` for local no-credential exploration.
- Concept documentation for sessions, checkpoints, tool actions, and workflows.
- Pi-like guided planning example.

### Changed

- README reorganized into a shorter entry point with deeper concept docs.
- Release line moved forward to `0.1.1` instead of moving the existing `v0.1.0`
  tag.

## 0.1.0 - 2026-06-29

Initial MVP for a human-centered Python agent harness.

### Added

- Core `Agent`, `Session`, `Compass`, `Checkpoint`, `Tool`, and `Workflow` primitives.
- OpenAI-compatible chat completions provider using standard `OPENAI_*` environment variables.
- Controlled tool execution with checkpoint pause, approve, reject, and resume flows.
- Agent JSON action protocol for model-requested tool calls.
- Automatic tool manifest injection into agent instructions.
- Pausable workflows with session-managed checkpoints.
- JSON-safe session snapshots and snapshot file persistence.
- Minimal `pyxis` CLI with `doctor`, `run`, and `--save-snapshot`.
- English and Simplified Chinese README documentation.
- Live examples for provider calls and model-driven tool calls.

### Notes

- Snapshot loading is currently inspection-only; it does not restore Python callables.
- Provider support currently targets OpenAI-compatible chat completions APIs.
