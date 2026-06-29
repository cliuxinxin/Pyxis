"""Run a live model through the Pyxis tool-call protocol."""

from __future__ import annotations

from _env import load_env_file, require_env

from pyxis import Agent, OpenAICompatibleProvider, Pyxis, tool


@tool(risk="low", action="summarize")
def summarize(text: str) -> str:
    """Summarize text into a short phrase."""

    cleaned = " ".join(text.split())
    return f"summary: {cleaned[:80]}"


@tool(risk="high", action="file_write")
def pretend_write_file(path: str, content: str) -> str:
    """Pretend to write content to a file."""

    return f"would write {len(content)} characters to {path}"


def main() -> None:
    load_env_file()

    provider = OpenAICompatibleProvider(
        model=require_env("OPENAI_MODEL"),
        temperature=0,
    )
    agent = Agent(
        name="navigator",
        instructions=(
            "Use a tool when it is useful. If you use a tool, return only the "
            "Pyxis action JSON. Do not wrap JSON in markdown. Do not explain the "
            "JSON. Use normal text only when no tool is needed."
        ),
        provider=provider,
        tools=[summarize, pretend_write_file],
    )

    session = Pyxis(agent=agent).session()

    low_risk = session.navigate(
        "Use the summarize tool to summarize this text: "
        "Pyxis keeps AI tasks calm, controllable, observable, and human-led."
    )
    print("Low-risk tool result:")
    print(low_risk.output)

    high_risk = session.navigate(
        "Use the pretend_write_file tool to save 'hello from Pyxis' to notes.txt."
    )
    print("\nHigh-risk tool result:")
    print(high_risk.output)

    tool_result = high_risk.metadata.get("tool_result")
    if tool_result and tool_result.requires_confirmation and tool_result.checkpoint:
        checkpoint = tool_result.checkpoint
        print(f"Checkpoint: {checkpoint.id} ({checkpoint.status.value})")


if __name__ == "__main__":
    main()
