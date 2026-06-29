"""Run Pyxis with an OpenAI-compatible chat completions provider."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from pyxis import Agent, OpenAICompatibleProvider, Pyxis

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = REPO_ROOT / ".env.local"


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs without overriding existing env vars."""

    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    load_env_file(ENV_FILE)

    provider = OpenAICompatibleProvider(
        model=require_env("OPENAI_MODEL"),
    )
    agent = Agent(
        name="navigator",
        instructions=(
            "You are Pyxis, a calm and concise navigation layer for controllable "
            "AI workflows. Propose clear next steps and keep the human in control."
        ),
        provider=provider,
    )

    prompt = " ".join(sys.argv[1:]) or "帮我规划一个可控的竞品研究流程"
    result = Pyxis(agent=agent).navigate(prompt)

    print(result.output)


if __name__ == "__main__":
    main()
