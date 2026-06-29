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

## Near-Term

- Provider-native token streaming beyond the current turn-level session events.
- Stronger tool argument validation beyond the current signature-derived schema.
- Richer retry policies for tools beyond the current provider retry/backoff support.
- More detailed workflow step events.
- Custom snapshot redaction policies beyond the current default redaction keys.

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
