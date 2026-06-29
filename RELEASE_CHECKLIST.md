# Release Checklist

Use this checklist before publishing Pyxis.

## Version

- Package: `pyxis-ai`
- Import name: `pyxis`
- Current version: `0.1.0`
- Status: early MVP

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
python3 -m zipfile --list dist/pyxis_ai-0.1.0-py3-none-any.whl
tar -tzf dist/pyxis_ai-0.1.0.tar.gz
```

Install the wheel in a clean environment and smoke test imports and CLI:

```bash
python3 -m venv /tmp/pyxis-release-check
/tmp/pyxis-release-check/bin/python -m pip install dist/pyxis_ai-0.1.0-py3-none-any.whl
/tmp/pyxis-release-check/bin/python -c "import pyxis; print(pyxis.Pyxis)"
/tmp/pyxis-release-check/bin/pyxis --env-file .env.example doctor
```

## Public API Review

The top-level `pyxis` package should expose the main user-facing primitives:

- `Agent`
- `Pyxis`
- `Session`
- `Compass`
- `Checkpoint`
- `ControlPolicy`
- `Tool` / `tool`
- `Workflow`
- `MockProvider`
- `OpenAICompatibleProvider`
- `load_snapshot` / `save_snapshot`
- `parse_agent_action`

## Documentation Review

- `README.md` explains install, CLI, providers, snapshots, tools, and workflows.
- `README.zh-CN.md` mirrors the main usage path in Chinese.
- `CHANGELOG.md` describes the unreleased `0.1.0` MVP.
- `CONTRIBUTING.md` documents local development and safety expectations.
- `docs/roadmap.md` lists current, near-term, later, and non-goal items.

## Secret Safety

- Real credentials belong in `.env.local`.
- `.env.local` must remain ignored by git.
- Release artifacts must not include `.env.local`.

## Known MVP Limits

- Snapshot loading is inspection-only and does not restore Python callables.
- Tool argument schemas are descriptive rather than strongly validated.
- Provider support targets OpenAI-compatible chat completions APIs.
- CLI checkpoint approval is not interactive yet.

## 0.1.0 Audit Notes

The current release candidate has been checked with:

- `PYTHONPATH=src python3 -m pytest`
- `python3 -m ruff check .`
- `python3 -m build`
- wheel content inspection
- sdist content inspection
- wheel install in a temporary virtual environment
- installed `pyxis doctor` smoke test
