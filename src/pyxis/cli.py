"""Command line interface for Pyxis."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from pyxis import Agent, OpenAICompatibleProvider, Pyxis

DEFAULT_ENV_FILE = Path(".env.local")
REQUIRED_OPENAI_ENV = ("OPENAI_BASE_URL", "OPENAI_API_KEY", "OPENAI_MODEL")


def load_env_file(path: str | Path = DEFAULT_ENV_FILE) -> None:
    """Load simple KEY=VALUE pairs without overriding existing env vars."""

    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pyxis",
        description="A minimal, human-centered Python agent harness.",
    )
    parser.add_argument(
        "--env-file",
        default=str(DEFAULT_ENV_FILE),
        help="Path to a local env file. Defaults to .env.local.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="Check local provider configuration.")

    run = subparsers.add_parser("run", help="Run one prompt through a provider-backed agent.")
    run.add_argument("prompt", nargs="+", help="Prompt to send to the agent.")
    run.add_argument(
        "--save-snapshot",
        help="Optional path where a session audit snapshot should be saved.",
    )
    run.add_argument(
        "--instructions",
        default=(
            "You are Pyxis, a calm and concise navigation layer for controllable "
            "AI workflows. Keep the human in control."
        ),
        help="Agent instructions.",
    )
    run.add_argument(
        "--approve",
        action="store_true",
        help="Automatically approve a pending checkpoint produced by the run.",
    )

    return parser


def cmd_doctor() -> int:
    missing = [name for name in REQUIRED_OPENAI_ENV if not os.getenv(name)]
    for name in REQUIRED_OPENAI_ENV:
        status = "set" if os.getenv(name) else "missing"
        print(f"{name}: {status}")
    return 1 if missing else 0


def cmd_run(args: argparse.Namespace) -> int:
    missing = [name for name in REQUIRED_OPENAI_ENV if not os.getenv(name)]
    if missing:
        print(f"Missing required environment variable(s): {', '.join(missing)}", file=sys.stderr)
        return 1

    provider = OpenAICompatibleProvider(model=os.environ["OPENAI_MODEL"])
    agent = Agent(
        name="navigator",
        instructions=args.instructions,
        provider=provider,
    )
    session = Pyxis(agent=agent).session()
    result = session.navigate(" ".join(args.prompt))
    print(result.output)
    _maybe_handle_checkpoint(args, session, result)

    if args.save_snapshot:
        path = session.save_snapshot(args.save_snapshot)
        print(f"Snapshot saved to {path}")

    return 0


def _maybe_handle_checkpoint(
    args: argparse.Namespace,
    session,
    result,
) -> None:
    tool_result = result.metadata.get("tool_result")
    if not tool_result or not getattr(tool_result, "requires_confirmation", False):
        return

    checkpoint = getattr(tool_result, "checkpoint", None)
    if checkpoint is None:
        return

    approve = args.approve
    if not approve:
        answer = input(f"Approve checkpoint {checkpoint.id}? [y/N] ").strip().lower()
        approve = answer in {"y", "yes"}

    if not approve:
        print(f"Checkpoint left pending: {checkpoint.id}")
        return

    session.approve_checkpoint(checkpoint.id)
    resumed = session.resume_checkpoint(checkpoint.id)
    print(resumed.output)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    load_env_file(args.env_file)

    if args.command == "doctor":
        return cmd_doctor()
    if args.command == "run":
        return cmd_run(args)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
