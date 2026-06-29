"""Run Pyxis with an OpenAI-compatible chat completions provider."""

from __future__ import annotations

import sys

from _env import load_env_file, require_env

from pyxis import Agent, OpenAICompatibleProvider, Pyxis


def main() -> None:
    load_env_file()

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
