# Pyxis Roadmap

Pyxis is a minimal, human-centered Python agent harness for controllable AI
workflows.

## Current MVP

- Provider-backed agent sessions.
- OpenAI-compatible provider.
- Tool manifest injection.
- Agent JSON action protocol.
- Checkpointed tool execution.
- Pausable workflows.
- Session snapshots and snapshot files.
- Minimal CLI.
- Structured dialogue analysis with intent, goal, clarification, constraints,
  preferences, and response styling.
- Consent-oriented checkpoint details and CLI approval prompts.
- Bounded in-process memory for user preferences, project context, and
  scratchpad state.
- Reflective workflow steps for ask, reflect, and revise loops.
- Provider-native token streaming for OpenAI-compatible providers.
- `pyxis demo` and Pi-like guided planning example.
- Concept documentation for sessions, checkpoints, tool actions, and workflows.
- Snapshot restore through registered callable catalogs.
- Provider contract fields for usage, finish reasons, timeout, and cancellation.

## Near-Term

- Provider contract finalization for stream retry semantics.
- Policy matrix for approval mode, action allow/deny lists, and risk overrides.
- Richer retry policies for tools beyond the current provider retry/backoff support.
- More detailed workflow step events.
- Custom snapshot redaction policies beyond the current default redaction keys.
- Versioned release automation beyond the current manual checklist.

## 1.0 Readiness

- Public API reference and compatibility policy.
- Strong tool argument validation.
- Snapshot restore for sessions, pending tool calls, and workflows.
- Stable provider protocol for complete and stream calls.
- Complete policy and consent semantics.
- Stable event schema and observability coverage.
- CLI inspect, memory, stream, and workflow demo commands.
- Expanded CI packaging and install checks.
- Synchronized English and Chinese documentation.

## Later

- Optional persistent session store.
- Workflow resume from registered callable catalogs.
- Multi-agent coordination primitives.
- Provider adapters beyond OpenAI-compatible APIs.
- Rich CLI output beyond the current basic checkpoint approval flow.

## Non-Goals For The Core

- Hidden autonomous loops.
- Mandatory vector databases.
- Mandatory web frameworks.
- Provider-specific logic in core session orchestration.
