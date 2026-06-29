"""Command line interface for Pyxis."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from pyxis import (
    Agent,
    MockProvider,
    OpenAICompatibleProvider,
    ProjectContext,
    Pyxis,
    SessionMemory,
    UserPreferences,
    Workflow,
    load_snapshot,
    tool,
)

DEFAULT_ENV_FILE = Path(".env.local")
DEFAULT_MEMORY_FILE = Path(".pyxis-memory.json")
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
    parser.add_argument(
        "--memory-file",
        default=str(DEFAULT_MEMORY_FILE),
        help="Path to a local CLI memory file. Defaults to .pyxis-memory.json.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="Check local provider configuration.")
    subparsers.add_parser("demo", help="Run a local Pyxis demo without provider credentials.")

    inspect = subparsers.add_parser("inspect", help="Inspect a Pyxis snapshot file.")
    inspect.add_argument("snapshot", help="Path to a session snapshot JSON file.")
    inspect.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    memory = subparsers.add_parser("memory", help="Inspect or clear local CLI memory.")
    memory_subparsers = memory.add_subparsers(dest="memory_command", required=True)
    memory_subparsers.add_parser("show", help="Print local CLI memory.")
    memory_subparsers.add_parser("clear", help="Clear local CLI memory.")

    workflow = subparsers.add_parser("workflow", help="Run local workflow demos.")
    workflow_subparsers = workflow.add_subparsers(dest="workflow_command", required=True)
    workflow_subparsers.add_parser("demo", help="Run a checkpointed workflow demo.")

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
    run.add_argument(
        "--stream",
        action="store_true",
        help="Stream provider-native deltas when the provider supports streaming.",
    )

    return parser


def cmd_doctor() -> int:
    missing = [name for name in REQUIRED_OPENAI_ENV if not os.getenv(name)]
    for name in REQUIRED_OPENAI_ENV:
        status = "set" if os.getenv(name) else "missing"
        print(f"{name}: {status}")
    return 1 if missing else 0


def cmd_inspect(args: argparse.Namespace) -> int:
    try:
        snapshot = load_snapshot(args.snapshot)
    except (OSError, ValueError) as exc:
        print(f"Could not inspect snapshot: {exc}", file=sys.stderr)
        return 1

    summary = _snapshot_summary(snapshot)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    print("Pyxis snapshot")
    print("--------------")
    for key, value in summary.items():
        print(f"{key}: {value}")
    return 0


def _snapshot_summary(snapshot: dict) -> dict[str, object]:
    agent = snapshot.get("agent") if isinstance(snapshot.get("agent"), dict) else {}
    dialogue = snapshot.get("dialogue") if isinstance(snapshot.get("dialogue"), dict) else {}
    messages = dialogue.get("messages") if isinstance(dialogue.get("messages"), list) else []
    tools = agent.get("tools") if isinstance(agent.get("tools"), list) else []
    events = snapshot.get("events") if isinstance(snapshot.get("events"), list) else []
    checkpoints = (
        snapshot.get("checkpoints") if isinstance(snapshot.get("checkpoints"), list) else []
    )
    pending_tool_calls = (
        snapshot.get("pending_tool_calls")
        if isinstance(snapshot.get("pending_tool_calls"), dict)
        else {}
    )
    pending_workflows = (
        snapshot.get("pending_workflows")
        if isinstance(snapshot.get("pending_workflows"), dict)
        else {}
    )
    return {
        "agent": agent.get("name") or "unknown",
        "tools": len(tools),
        "messages": len(messages),
        "events": len(events),
        "checkpoints": len(checkpoints),
        "pending_tool_calls": len(pending_tool_calls),
        "pending_workflows": len(pending_workflows),
    }


def cmd_memory(args: argparse.Namespace) -> int:
    memory_path = Path(args.memory_file)
    if args.memory_command == "show":
        memory = load_memory_file(memory_path)
        print(json.dumps(memory.to_dict(), indent=2, sort_keys=True))
        return 0
    if args.memory_command == "clear":
        save_memory_file(SessionMemory(), memory_path)
        print(f"Memory cleared at {memory_path}")
        return 0
    return 2


def load_memory_file(path: str | Path) -> SessionMemory:
    memory_path = Path(path)
    if not memory_path.exists():
        return SessionMemory()

    try:
        data = json.loads(memory_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return SessionMemory()
    if not isinstance(data, dict):
        return SessionMemory()

    preferences = data.get("preferences") if isinstance(data.get("preferences"), dict) else {}
    project_data = data.get("project") if isinstance(data.get("project"), dict) else {}
    scratchpad = data.get("scratchpad") if isinstance(data.get("scratchpad"), dict) else {}
    project_metadata = (
        project_data.get("metadata") if isinstance(project_data.get("metadata"), dict) else {}
    )
    return SessionMemory(
        preferences=UserPreferences(values=dict(preferences)),
        project=ProjectContext(
            name=project_data.get("name") if isinstance(project_data.get("name"), str) else None,
            description=(
                project_data.get("description")
                if isinstance(project_data.get("description"), str)
                else None
            ),
            metadata=dict(project_metadata),
        ),
        scratchpad=dict(scratchpad),
    )


def save_memory_file(memory: SessionMemory, path: str | Path) -> Path:
    memory_path = Path(path)
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    memory_path.write_text(
        json.dumps(memory.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return memory_path


def cmd_demo() -> int:
    memory = SessionMemory()
    memory.set_preference("tone", "concise")
    memory.set_preference("approval_mode", "strict")
    memory.set_project_context(name="Pyxis", description="Human-centered agent harness")

    @tool(risk="high", action="file_write")
    def write_file(path: str, content: str) -> str:
        """Pretend to write content to a file."""

        return f"would write {len(content)} characters to {path}"

    agent = Agent(
        name="navigator",
        instructions="Help the user think clearly before acting.",
        provider=MockProvider(output="Here is a concise, controllable plan."),
        tools=[write_file],
        memory=memory,
    )
    session = Pyxis(agent=agent).session()

    print("Pyxis demo")
    print("----------")

    clarification = session.navigate("帮我弄一下")
    print(f"Clarification: {clarification.output}")

    plan = session.navigate("Plan a concise research workflow")
    print(f"Plan: {plan.output}")

    paused_tool = session.call_tool("write_file", "notes.txt", content="hello")
    if paused_tool.checkpoint:
        checkpoint = paused_tool.checkpoint
        print("Checkpoint:")
        print(f"  Action: {checkpoint.action}")
        print(f"  Reason: {checkpoint.risk_reason}")
        print(f"  Preview: {checkpoint.preview}")

    workflow = (
        Workflow("guided-draft")
        .step("clean", lambda text: text.strip())
        .reflect("Check if the output matches the user's goal")
        .step("finish", lambda text: f"Final: {text}")
    )
    paused_workflow = session.run(workflow, "  Pyxis keeps the human in control.  ")
    if paused_workflow.checkpoint:
        print("Workflow reflection:")
        print(f"  {paused_workflow.checkpoint.preview}")

    print("Memory:")
    print(f"  {memory.to_dict()}")
    return 0


def cmd_workflow(args: argparse.Namespace) -> int:
    if args.workflow_command != "demo":
        return 2

    workflow = (
        Workflow("release-notes")
        .step("trim", lambda text: text.strip())
        .reflect("Check whether this summary is ready for release notes.", name="review")
        .step("finish", lambda text: f"Ready: {text}")
    )
    session = Pyxis(agent=Agent(name="navigator")).session()
    result = session.run(workflow, "  Pyxis keeps people in control.  ")

    print("Pyxis workflow demo")
    print("-------------------")
    print(f"Workflow: {result.name}")
    print(f"Steps: {', '.join(result.steps) or 'none'}")
    if result.checkpoint:
        print(f"Paused: {result.checkpoint.id}")
        print(f"Action: {result.checkpoint.action}")
        print(f"Preview: {result.checkpoint.preview}")
    else:
        print(f"Output: {result.output}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    missing = [name for name in REQUIRED_OPENAI_ENV if not os.getenv(name)]
    if missing:
        print(f"Missing required environment variable(s): {', '.join(missing)}", file=sys.stderr)
        return 1

    provider = OpenAICompatibleProvider(model=os.environ["OPENAI_MODEL"])
    memory = load_memory_file(args.memory_file)
    agent = Agent(
        name="navigator",
        instructions=args.instructions,
        provider=provider,
        memory=memory,
    )
    session = Pyxis(agent=agent).session()
    prompt = " ".join(args.prompt)
    if args.stream:
        _run_streaming_prompt(session, prompt)
    else:
        result = session.navigate(prompt)
        print(result.output)
        _maybe_handle_checkpoint(args, session, result)

    if args.save_snapshot:
        path = session.save_snapshot(args.save_snapshot)
        print(f"Snapshot saved to {path}")

    save_memory_file(memory, args.memory_file)
    return 0


def _run_streaming_prompt(session, prompt: str) -> None:
    saw_delta = False
    last_output = ""
    for event in session.stream(prompt):
        if event.type == "delta":
            saw_delta = True
            print(event.data.get("text", ""), end="", flush=True)
        elif event.type == "result":
            last_output = str(event.data.get("output", ""))
        elif event.type == "checkpoint":
            checkpoint = event.data.get("checkpoint") or {}
            print()
            print(f"Checkpoint pending: {checkpoint.get('id', 'unknown')}")

    if saw_delta:
        print()
    elif last_output:
        print(last_output)


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
        answer = input(_format_checkpoint_prompt(checkpoint)).strip().lower()
        approve = answer in {"y", "yes"}

    if not approve:
        print(f"Checkpoint left pending: {checkpoint.id}")
        return

    session.approve_checkpoint(checkpoint.id)
    resumed = session.resume_checkpoint(checkpoint.id)
    print(resumed.output)


def _format_checkpoint_prompt(checkpoint) -> str:
    summary = getattr(
        checkpoint,
        "summary",
        None,
    ) or "Pyxis wants to run an action that needs your approval."
    action = getattr(checkpoint, "action", "unknown")
    reason = getattr(checkpoint, "risk_reason", None) or getattr(
        checkpoint,
        "reason",
        "This action requires confirmation.",
    )
    preview = getattr(checkpoint, "preview", None)

    lines = [
        "",
        summary,
        "",
        f"Action: {action}",
        f"Reason: {reason}",
    ]
    if preview:
        lines.append(f"Preview: {preview}")
    lines.extend(["", f"Checkpoint: {checkpoint.id}", "", "Approve? [y/N] "])
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    load_env_file(args.env_file)

    if args.command == "doctor":
        return cmd_doctor()
    if args.command == "demo":
        return cmd_demo()
    if args.command == "inspect":
        return cmd_inspect(args)
    if args.command == "memory":
        return cmd_memory(args)
    if args.command == "workflow":
        return cmd_workflow(args)
    if args.command == "run":
        return cmd_run(args)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
