import json

import pytest

from pyxis import Agent, MockProvider, Pyxis, Workflow, load_snapshot, save_snapshot, tool


def test_session_snapshot_is_json_serializable() -> None:
    @tool(risk="high", action="file_write")
    def write_file(path: str) -> str:
        return path

    agent = Agent(name="navigator", provider=MockProvider(output="hello"), tools=[write_file])
    session = Pyxis(agent=agent).session()
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


def test_session_save_snapshot_round_trips_json(tmp_path) -> None:
    session = Pyxis(agent=Agent(name="navigator")).session()
    session.navigate("hello")

    path = session.save_snapshot(tmp_path / "audit" / "session.json")
    loaded = load_snapshot(path)

    assert path.exists()
    assert loaded["agent"]["name"] == "navigator"
    assert loaded["dialogue"]["messages"][0]["content"] == "hello"


def test_save_snapshot_helper_round_trips_json(tmp_path) -> None:
    path = save_snapshot({"kind": "session", "events": []}, tmp_path / "snapshot.json")

    assert load_snapshot(path) == {"kind": "session", "events": []}


def test_load_snapshot_rejects_non_object_json(tmp_path) -> None:
    path = tmp_path / "snapshot.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError):
        load_snapshot(path)


def test_session_snapshot_can_redact_sensitive_fields() -> None:
    @tool(risk="high", action="file_write")
    def write_file(path: str, content: str, api_key: str) -> str:
        return path

    session = Pyxis(agent=Agent(name="navigator", tools=[write_file])).session()
    paused = session.call_tool(
        "write_file",
        "demo.txt",
        content="private content",
        api_key="secret-key",
    )
    assert paused.checkpoint is not None

    snapshot = session.snapshot(redact=True)
    pending = snapshot["pending_tool_calls"][paused.checkpoint.id]
    checkpoint = snapshot["checkpoints"][0]

    assert pending["kwargs"]["content"] == "[REDACTED]"
    assert pending["kwargs"]["api_key"] == "[REDACTED]"
    assert checkpoint["payload"]["kwargs"]["content"] == "[REDACTED]"
    assert checkpoint["payload"]["kwargs"]["api_key"] == "[REDACTED]"


def test_session_save_snapshot_can_redact(tmp_path) -> None:
    session = Pyxis(agent=Agent(name="navigator")).session()
    session.navigate("private message")

    path = session.save_snapshot(tmp_path / "session.json", redact=True)
    loaded = load_snapshot(path)

    assert loaded["dialogue"]["messages"][0]["content"] == "[REDACTED]"
