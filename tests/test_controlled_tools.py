import pytest

from pyxis import Agent, CheckpointStatus, Pyxis, tool
from pyxis.errors import (
    CheckpointNotApproved,
    CheckpointRejected,
    ToolNotFound,
    ToolValidationError,
)


def test_low_risk_tool_executes_immediately() -> None:
    @tool(risk="low", action="summarize")
    def summarize(text: str) -> str:
        return text[:5]

    session = Pyxis(agent=Agent(name="navigator", tools=[summarize])).session()

    result = session.call_tool("summarize", "pyxis-agent")

    assert result.output == "pyxis"
    assert result.requires_confirmation is False
    assert result.checkpoint is None
    assert len(session.checkpoints) == 0


def test_high_risk_tool_pauses_with_checkpoint() -> None:
    calls: list[str] = []

    @tool(risk="high", action="file_write")
    def write_file(path: str) -> str:
        calls.append(path)
        return "written"

    session = Pyxis(agent=Agent(name="navigator", tools=[write_file])).session()

    result = session.call_tool("write_file", "demo.txt")

    assert result.output is None
    assert result.requires_confirmation is True
    assert result.checkpoint is not None
    assert result.checkpoint.status == CheckpointStatus.PENDING
    assert result.checkpoint.payload["tool"] == "write_file"
    assert result.checkpoint.summary == "Pyxis wants to run tool 'write_file'."
    assert result.checkpoint.risk_reason == "This is a high-risk file_write action."
    assert result.checkpoint.preview == "write_file('demo.txt')"
    assert result.checkpoint.options == ["approve", "reject"]
    assert calls == []


def test_approved_checkpoint_resumes_tool_call() -> None:
    calls: list[str] = []

    @tool(risk="high", action="file_write")
    def write_file(path: str) -> str:
        calls.append(path)
        return f"wrote {path}"

    session = Pyxis(agent=Agent(name="navigator", tools=[write_file])).session()
    paused = session.call_tool("write_file", "demo.txt")
    assert paused.checkpoint is not None

    session.approve_checkpoint(paused.checkpoint.id)
    resumed = session.resume_checkpoint(paused.checkpoint.id)

    assert resumed.output == "wrote demo.txt"
    assert calls == ["demo.txt"]
    assert paused.checkpoint.id not in session.pending_tool_calls


def test_pending_checkpoint_cannot_resume_before_approval() -> None:
    @tool(risk="high", action="shell_exec")
    def run_shell(command: str) -> str:
        return command

    session = Pyxis(agent=Agent(name="navigator", tools=[run_shell])).session()
    paused = session.call_tool("run_shell", "echo hi")
    assert paused.checkpoint is not None

    with pytest.raises(CheckpointNotApproved):
        session.resume_checkpoint(paused.checkpoint.id)


def test_rejected_checkpoint_cannot_resume() -> None:
    @tool(risk="high", action="shell_exec")
    def run_shell(command: str) -> str:
        return command

    session = Pyxis(agent=Agent(name="navigator", tools=[run_shell])).session()
    paused = session.call_tool("run_shell", "echo hi")
    assert paused.checkpoint is not None

    session.reject_checkpoint(paused.checkpoint.id)

    with pytest.raises(CheckpointRejected):
        session.resume_checkpoint(paused.checkpoint.id)


def test_missing_tool_raises_clear_error() -> None:
    session = Pyxis(agent=Agent(name="navigator")).session()

    with pytest.raises(ToolNotFound):
        session.call_tool("missing")


def test_invalid_tool_arguments_fail_before_checkpoint() -> None:
    @tool(risk="high", action="file_write")
    def write_file(path: str, content: str) -> str:
        return path

    session = Pyxis(agent=Agent(name="navigator", tools=[write_file])).session()

    with pytest.raises(ToolValidationError, match="missing a required argument"):
        session.call_tool("write_file", "demo.txt")

    assert session.checkpoints == []
    assert session.pending_tool_calls == {}
    assert [event.type for event in session.events] == ["ToolValidationFailed"]
