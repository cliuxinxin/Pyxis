import pytest

from pyxis import Agent, CheckpointStatus, ControlPolicy, Pyxis, tool
from pyxis.errors import (
    CheckpointNotApproved,
    CheckpointRejected,
    PolicyDeniedError,
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
    assert result.checkpoint.risk_reason == (
        "Action 'file_write' requires confirmation with effective risk 'high'."
    )
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


def test_policy_denies_action_before_tool_execution() -> None:
    calls: list[str] = []

    @tool(risk="low", action="network_post")
    def post(url: str) -> str:
        calls.append(url)
        return url

    session = Pyxis(
        agent=Agent(name="navigator", tools=[post]),
        policy=ControlPolicy(deny_actions={"network_post"}),
    ).session()

    with pytest.raises(PolicyDeniedError, match="denied by policy"):
        session.call_tool("post", "https://example.com")

    assert calls == []
    assert session.checkpoints == []
    assert [event.type for event in session.events] == [
        "ToolCallRequested",
        "PolicyDenied",
    ]


def test_policy_risk_override_and_custom_options_shape_checkpoint() -> None:
    @tool(risk="low", action="file_write")
    def write_file(path: str) -> str:
        return path

    policy = ControlPolicy(
        risk_overrides={"file_write": "high"},
        checkpoint_options=["approve", "reject", "revise"],
    )
    session = Pyxis(agent=Agent(name="navigator", tools=[write_file]), policy=policy).session()

    result = session.call_tool("write_file", "demo.txt")

    assert result.requires_confirmation
    assert result.checkpoint is not None
    assert result.checkpoint.options == ["approve", "reject", "revise"]
    assert result.checkpoint.payload["risk"] == "low"
    assert result.checkpoint.payload["effective_risk"] == "high"
    assert result.metadata["effective_risk"] == "high"


def test_strict_policy_confirms_unlisted_actions() -> None:
    @tool(risk="low", action="summarize")
    def summarize(text: str) -> str:
        return text[:5]

    session = Pyxis(
        agent=Agent(name="navigator", tools=[summarize]),
        policy=ControlPolicy.strict(),
    ).session()

    result = session.call_tool("summarize", "pyxis-agent")

    assert result.requires_confirmation
    assert result.checkpoint is not None
    assert result.checkpoint.risk_reason == "Strict approval mode requires confirmation."


def test_permissive_policy_allows_high_risk_unless_explicitly_required() -> None:
    calls: list[str] = []

    @tool(risk="high", action="file_write")
    def write_file(path: str) -> str:
        calls.append(path)
        return path

    session = Pyxis(
        agent=Agent(name="navigator", tools=[write_file]),
        policy=ControlPolicy.permissive(),
    ).session()

    result = session.call_tool("write_file", "demo.txt")

    assert result.output == "demo.txt"
    assert result.requires_confirmation is False
    assert session.checkpoints == []
    assert calls == ["demo.txt"]
