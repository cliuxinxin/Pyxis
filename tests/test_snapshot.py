import json

from pyxis import Agent, Pyxis, Workflow, tool


def test_session_snapshot_is_json_serializable() -> None:
    @tool(risk="high", action="file_write")
    def write_file(path: str) -> str:
        return path

    session = Pyxis(agent=Agent(name="navigator", tools=[write_file])).session()
    session.navigate("hello")
    paused = session.call_tool("write_file", "demo.txt")
    assert paused.checkpoint is not None

    snapshot = session.snapshot()

    json.dumps(snapshot)
    assert snapshot["agent"]["name"] == "navigator"
    assert snapshot["agent"]["tools"][0]["name"] == "write_file"
    assert snapshot["dialogue"]["messages"][0]["role"] == "user"
    assert snapshot["checkpoints"][0]["status"] == "pending"
    assert snapshot["pending_tool_calls"][paused.checkpoint.id]["name"] == "write_file"
    assert snapshot["events"][0]["type"] == "UserMessageReceived"


def test_session_snapshot_includes_pending_workflow() -> None:
    workflow = (
        Workflow("draft")
        .step("clean", lambda value: value.strip())
        .checkpoint("Review cleaned text.")
        .step("report", lambda value: f"Report: {value}")
    )
    session = Pyxis(agent=Agent(name="navigator")).session()

    result = session.run(workflow, "  Pyxis  ")
    assert result.checkpoint is not None
    snapshot = session.snapshot()

    pending = snapshot["pending_workflows"][result.checkpoint.id]
    assert pending["workflow"] == "draft"
    assert pending["state"] == "Pyxis"
    assert pending["next_step"] == 2
    assert pending["completed_steps"] == ["clean"]
