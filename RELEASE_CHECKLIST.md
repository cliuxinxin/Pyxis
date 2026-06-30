# Release Checklist

Use this checklist before publishing Pyxis.

## Version

- Package: `pyxis-ai`
- Import name: `pyxis`
- Current version: `1.0.1`
- Status: patch release candidate

## Required Checks

Run from the repository root:

```bash
PYTHONPATH=src python3 -m pytest
python3 -m ruff check .
python3 -m build
python3 -m twine check dist/*
```

Confirm no local secrets or legacy custom environment variables are tracked:

```bash
rg "<legacy-custom-env-prefix>|sk-|<known-secret-fragment>" .
```

Inspect built artifacts:

```bash
python3 -m zipfile --list dist/pyxis_ai-1.0.1-py3-none-any.whl
tar -tzf dist/pyxis_ai-1.0.1.tar.gz
```

Install the wheel in a clean environment and smoke test imports and CLI:

```bash
python3 -m venv /tmp/pyxis-release-check
/tmp/pyxis-release-check/bin/python -m pip install dist/pyxis_ai-1.0.1-py3-none-any.whl
/tmp/pyxis-release-check/bin/python -c "import pyxis; print(pyxis.Pyxis)"
/tmp/pyxis-release-check/bin/pyxis --env-file .env.example doctor
/tmp/pyxis-release-check/bin/pyxis --env-file missing.env demo
/tmp/pyxis-release-check/bin/pyxis --env-file missing.env workflow demo
/tmp/pyxis-release-check/bin/pyxis --env-file missing.env memory show
printf '{"agent":{"name":"navigator"},"events":[]}' > /tmp/pyxis-release-check/session-audit.json
/tmp/pyxis-release-check/bin/pyxis --env-file missing.env inspect /tmp/pyxis-release-check/session-audit.json
```

After pushing to GitHub, confirm the CI workflow passes on `main`.

## GitHub Actions Publish

Create a repository secret before publishing:

- Secret name: `PYPI_API_TOKEN`
- Secret value: the PyPI project or account token

The token must stay in GitHub Secrets. Do not commit it to the repository.

Publish through GitHub:

```bash
git push origin main
git tag -a v1.0.1 -m "Pyxis 1.0.1"
git push origin v1.0.1
```

Then create a GitHub Release for `v1.0.1` and click **Publish release**. The
`Publish` workflow builds the package, checks metadata, and uploads `dist/*` to
PyPI using `PYPI_API_TOKEN`.

The workflow can also be run manually with `workflow_dispatch` after confirming
the target version has not already been published on PyPI.

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
- `EventSink` / `NullEventSink` / `InMemoryEventSink`
- `Intent` / `UserGoal` / `Clarification`
- `SessionMemory` / `UserPreferences` / `ProjectContext`
- `MemoryStore` / `MemoryItem` / `NoMemoryStore` / `InMemoryStore`
- `StructuredResult`
- `Tool` / `tool`
- `Workflow`
- `MockProvider`
- `OpenAICompatibleProvider`
- `ProviderConfigurationError` / `ProviderRequestError`
- `ProviderTimeoutError` / `ProviderCancelledError`
- `EventSinkError`
- `PolicyDeniedError`
- `load_snapshot` / `save_snapshot`
- `snapshot_metadata`
- `SnapshotMetadata` / `SnapshotRedactionPolicy`
- `restore_session` / `SnapshotRestoreCatalog`
- `parse_agent_action`

## Documentation Review

- `README.md` explains install, CLI, providers, snapshots, tools, and workflows.
- `API_REFERENCE.md` documents public API, compatibility, and deprecation policy.
- `README.zh-CN.md` mirrors the main usage path in Chinese.
- `CHANGELOG.md` describes the `1.0.1` release.
- `CONTRIBUTING.md` documents local development and safety expectations.
- `docs/roadmap.md` lists current, near-term, later, and non-goal items.
- `docs/concepts/` contains session, checkpoint, tool action, and workflow docs.
- `docs/concepts/providers.md` documents provider contracts.
- `docs/concepts/events.md` documents event schemas and observability contracts.
- `docs/concepts/memory.md` documents memory store boundaries.
- `docs/guides/async.md` documents async tools, providers, and workflows.
- `docs/guides/safety-control.md` documents policy and consent behavior.
- `docs/guides/cookbook.md` documents common usage patterns.
- `docs/guides/control-flow.md` documents programmable turn control.
- `docs/guides/provider-guide.md` documents custom provider implementation.
- `docs/guides/scheduling.md` documents scheduler boundaries.
- `docs/guides/structured-output.md` documents structured JSON output.
- `docs/guides/tool-authoring.md` documents tool metadata and validation.
- `docs/guides/migration.md` documents migration toward the 1.0 contract.
- `.github/workflows/ci.yml` runs tests, lint, build, package metadata, wheel
  install, import, and CLI smoke checks.
- `.github/workflows/publish.yml` publishes the built package to PyPI from a
  GitHub Release or manual workflow run.

## Secret Safety

- Real credentials belong in `.env.local`.
- `.env.local` must remain ignored by git.
- Release artifacts must not include `.env.local`.

## Known MVP Limits

- Provider adapters beyond OpenAI-compatible chat completions are not included yet.

## 1.0.1 Audit Notes

The current release candidate has been checked with:

- `PYTHONPATH=src python3 -m pytest`
- `python3 -m ruff check .`
- `python3 -m build`
- `python3 -m twine check dist/*`
- wheel content inspection
- sdist content inspection
- wheel install in a temporary virtual environment
- installed `pyxis doctor` smoke test
- installed `pyxis demo` smoke test
- local review of `.github/workflows/ci.yml`
