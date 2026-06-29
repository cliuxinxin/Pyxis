# Contributing

Pyxis is an early project. The goal is to keep the core small, controllable, and
easy to inspect.

## Development Setup

```bash
pip install -e ".[dev]"
```

Run checks before submitting changes:

```bash
PYTHONPATH=src python3 -m pytest
python3 -m ruff check .
```

## Design Principles

- Keep humans in control of risky actions.
- Prefer explicit checkpoints over hidden autonomous loops.
- Keep provider integrations behind small interfaces.
- Make events and state inspectable.
- Avoid adding dependencies unless they remove meaningful complexity.

## Secrets

Use `.env.local` for local provider credentials. It is ignored by git.

Do not commit real API keys, tokens, provider credentials, generated caches, or
local snapshot files containing sensitive data.

## Pull Request Checklist

- Tests pass.
- Ruff passes.
- Public API changes are documented.
- New behavior has focused tests.
- Risky actions remain checkpointable or explicitly documented.
