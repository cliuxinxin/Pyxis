# Changelog

All notable changes to Pyxis will be documented in this file.

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
