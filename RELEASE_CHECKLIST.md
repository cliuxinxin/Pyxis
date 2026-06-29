# Release Checklist

Use this checklist before publishing Pyxis.

## Version

- Package: `pyxis-ai`
- Import name: `pyxis`
- Current version: `0.1.1`
- Status: release candidate

## Required Checks

Run from the repository root:

```bash
PYTHONPATH=src python3 -m pytest
python3 -m ruff check .
python3 -m build
```

Confirm no local secrets or legacy custom environment variables are tracked:

```bash
rg "<legacy-custom-env-prefix>|sk-|<known-secret-fragment>" .
```

Inspect built artifacts:

```bash
python3 -m zipfile --list dist/pyxis_ai-0.1.1-py3-none-any.whl
tar -tzf dist/pyxis_ai-0.1.1.tar.gz
```

Install the wheel in a clean environment and smoke test imports and CLI:

```bash
python3 -m venv /tmp/pyxis-release-check
/tmp/pyxis-release-check/bin/python -m pip install dist/pyxis_ai-0.1.1-py3-none-any.whl
/tmp/pyxis-release-check/bin/python -c "import pyxis; print(pyxis.Pyxis)"
/tmp/pyxis-release-check/bin/pyxis --env-file .env.example doctor
/tmp/pyxis-release-check/bin/pyxis --env-file missing.env demo
```

After pushing to GitHub, confirm the CI workflow passes on `main`.

## Public API Review

The top-level `pyxis` package should expose the main user-facing primitives:

- `Agent`
- `Pyxis`
- `Session`
- `Compass`
- `Checkpoint`
- `CancellationToken`
- `CompletionRequest` / `CompletionResult` / `CompletionChunk`
- `ControlPolicy` / `ApprovalMode` / `PolicyDecision`
- `Event` / `EventLog` / `EventType` / `EventSchema` / `EVENT_SCHEMAS`
- `Intent` / `UserGoal` / `Clarification`
- `SessionMemory` / `UserPreferences` / `ProjectContext`
- `Tool` / `tool`
- `Workflow`
- `MockProvider`
- `OpenAICompatibleProvider`
- `ProviderConfigurationError` / `ProviderRequestError`
- `ProviderTimeoutError` / `ProviderCancelledError`
- `PolicyDeniedError`
- `load_snapshot` / `save_snapshot`
- `restore_session` / `SnapshotRestoreCatalog`
- `parse_agent_action`

## Documentation Review

- `README.md` explains install, CLI, providers, snapshots, tools, and workflows.
- `API_REFERENCE.md` documents public API, compatibility, and deprecation policy.
- `README.zh-CN.md` mirrors the main usage path in Chinese.
- `CHANGELOG.md` describes the `0.1.1` release.
- `CONTRIBUTING.md` documents local development and safety expectations.
- `docs/roadmap.md` lists current, near-term, later, and non-goal items.
- `docs/concepts/` contains session, checkpoint, tool action, and workflow docs.
- `docs/concepts/providers.md` documents provider contracts.
- `docs/concepts/events.md` documents event schemas and observability contracts.
- `docs/guides/safety-control.md` documents policy and consent behavior.
- `.github/workflows/ci.yml` runs tests, lint, and build checks.

## Secret Safety

- Real credentials belong in `.env.local`.
- `.env.local` must remain ignored by git.
- Release artifacts must not include `.env.local`.

## Known MVP Limits

- Stream retry semantics after a stream connection opens are still intentionally conservative.
- Provider adapters beyond OpenAI-compatible chat completions are not included yet.

## 0.1.1 Audit Notes

The current release candidate has been checked with:

- `PYTHONPATH=src python3 -m pytest`
- `python3 -m ruff check .`
- `python3 -m build`
- wheel content inspection
- sdist content inspection
- wheel install in a temporary virtual environment
- installed `pyxis doctor` smoke test
- installed `pyxis demo` smoke test
- local review of `.github/workflows/ci.yml`
