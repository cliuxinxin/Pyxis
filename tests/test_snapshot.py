import json

import pytest

from pyxis import (
    SNAPSHOT_SCHEMA_VERSION,
    Agent,
    MockProvider,
    Pyxis,
    SessionMemory,
    SnapshotRedactionPolicy,
    SnapshotRestoreCatalog,
    Workflow,
    load_snapshot,
    restore_session,
    save_snapshot,
    snapshot_metadata,
    tool,
)
from pyxis.errors import SnapshotRestoreError


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
    assert snapshot["metadata"] == {
        "kind": "pyxis.session",
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
    }
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


def test_snapshot_metadata_defaults_legacy_snapshots_to_v1() -> None:
    metadata = snapshot_metadata({"agent": {"name": "navigator"}})

    assert metadata.kind == "pyxis.session"
    assert metadata.schema_version == 1


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


def test_session_snapshot_can_use_custom_redaction_policy() -> None:
    @tool(risk="high", action="file_write")
    def write_file(path: str, customer_email: str, content: str) -> str:
        return path

    policy = SnapshotRedactionPolicy(
        redact_keys={"customer_email"},
        replacement="<hidden>",
    )
    session = Pyxis(agent=Agent(name="navigator", tools=[write_file])).session()
    paused = session.call_tool(
        "write_file",
        "demo.txt",
        customer_email="person@example.com",
        content="keep this visible",
    )
    assert paused.checkpoint is not None

    snapshot = session.snapshot(redact=True, redaction_policy=policy)
    pending = snapshot["pending_tool_calls"][paused.checkpoint.id]

    assert pending["kwargs"]["customer_email"] == "<hidden>"
    assert pending["kwargs"]["content"] == "keep this visible"


def test_session_save_snapshot_can_redact(tmp_path) -> None:
    session = Pyxis(agent=Agent(name="navigator")).session()
    session.navigate("private message")

    path = session.save_snapshot(tmp_path / "session.json", redact=True)
    loaded = load_snapshot(path)

    assert loaded["dialogue"]["messages"][0]["content"] == "[REDACTED]"


def test_restore_session_can_resume_pending_tool_call() -> None:
    calls: list[tuple[str, str]] = []

    @tool(risk="high", action="file_write")
    def write_file(path: str, content: str) -> str:
        calls.append((path, content))
        return f"wrote {path}"

    memory = SessionMemory()
    memory.set_preference("tone", "concise")
    session = Pyxis(agent=Agent(name="navigator", tools=[write_file], memory=memory)).session()
    paused = session.call_tool("write_file", "demo.txt", content="hello")
    assert paused.checkpoint is not None
    snapshot = session.snapshot()

    restored = restore_session(
        snapshot,
        catalog=SnapshotRestoreCatalog(tools={"write_file": write_file}),
    )

    assert restored.agent.name == "navigator"
    assert restored.agent.memory.to_dict()["preferences"] == {"tone": "concise"}
    assert restored.checkpoints[0].id == paused.checkpoint.id
    assert paused.checkpoint.id in restored.pending_tool_calls
    event_types = [event.type for event in restored.events]
    assert "ToolCallPaused" in event_types
    assert event_types[-1] == "SessionRestored"

    restored.approve_checkpoint(paused.checkpoint.id)
    result = restored.resume_checkpoint(paused.checkpoint.id)

    assert result.output == "wrote demo.txt"
    assert calls == [("demo.txt", "hello")]
    assert paused.checkpoint.id not in restored.pending_tool_calls


def test_restore_session_preserves_event_schema_version() -> None:
    session = Pyxis(agent=Agent(name="navigator", provider=MockProvider(output="hello"))).session()
    session.navigate("hello")
    snapshot = session.snapshot()
    snapshot["events"][0]["schema_version"] = 7

    restored = restore_session(snapshot, catalog=SnapshotRestoreCatalog())

    assert restored.events.all()[0].schema_version == 7


def test_restore_session_rejects_future_snapshot_schema_version() -> None:
    snapshot = {
        "metadata": {
            "kind": "pyxis.session",
            "schema_version": SNAPSHOT_SCHEMA_VERSION + 1,
        },
        "agent": {"name": "navigator", "tools": []},
    }

    with pytest.raises(SnapshotRestoreError, match="Unsupported snapshot schema version"):
        restore_session(snapshot, catalog=SnapshotRestoreCatalog())


def test_restore_session_can_resume_pending_workflow() -> None:
    workflow = (
        Workflow("draft")
        .step("clean", lambda value: value.strip())
        .checkpoint("Review cleaned text.", name="review")
        .step("finish", lambda value: f"Done: {value}")
    )
    session = Pyxis(agent=Agent(name="navigator")).session()
    paused = session.run(workflow, "  Pyxis  ")
    assert paused.checkpoint is not None

    restored = restore_session(
        session.snapshot(),
        catalog=SnapshotRestoreCatalog(workflows={"draft": workflow}),
    )

    assert paused.checkpoint.id in restored.pending_workflows
    restored.approve_checkpoint(paused.checkpoint.id)
    result = restored.resume_workflow(paused.checkpoint.id)

    assert result.output == "Done: Pyxis"
    assert result.steps == ["clean", "finish"]


def test_restore_session_requires_registered_pending_tool() -> None:
    @tool(risk="high", action="file_write")
    def write_file(path: str) -> str:
        return path

    session = Pyxis(agent=Agent(name="navigator", tools=[write_file])).session()
    session.call_tool("write_file", "demo.txt")

    with pytest.raises(SnapshotRestoreError, match="requires tool 'write_file'"):
        restore_session(session.snapshot(), catalog=SnapshotRestoreCatalog())


def test_restore_session_requires_registered_pending_workflow() -> None:
    workflow = Workflow("draft").checkpoint("Review.")
    session = Pyxis(agent=Agent(name="navigator")).session()
    session.run(workflow, "Pyxis")

    with pytest.raises(SnapshotRestoreError, match="requires workflow 'draft'"):
        restore_session(session.snapshot(), catalog=SnapshotRestoreCatalog())
