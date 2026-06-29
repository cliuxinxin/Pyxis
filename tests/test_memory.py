from pyxis import Agent, Pyxis, SessionMemory


def test_session_memory_stores_and_clears_preferences() -> None:
    memory = SessionMemory()

    memory.set_preference("tone", "concise")
    memory.set_preference("approval_mode", "strict")

    assert memory.get_preference("tone") == "concise"
    assert memory.to_dict()["preferences"] == {
        "tone": "concise",
        "approval_mode": "strict",
    }

    memory.clear_preferences("tone")
    assert memory.get_preference("tone") is None

    memory.clear_preferences()
    assert memory.to_dict()["preferences"] == {}


def test_session_memory_stores_and_clears_project_context() -> None:
    memory = SessionMemory()

    memory.set_project_context(
        name="Pyxis",
        description="Human-centered agent harness",
        metadata={"package": "pyxis-ai"},
    )

    assert memory.to_dict()["project"] == {
        "name": "Pyxis",
        "description": "Human-centered agent harness",
        "metadata": {"package": "pyxis-ai"},
    }

    memory.clear_project_context()
    assert memory.to_dict()["project"] == {
        "name": None,
        "description": None,
        "metadata": {},
    }


def test_session_snapshot_includes_bounded_memory() -> None:
    memory = SessionMemory()
    memory.set_preference("tone", "concise")
    memory.set_project_context(name="Pyxis")
    memory.set("working_note", "temporary")

    session = Pyxis(agent=Agent(name="navigator", memory=memory)).session()

    snapshot = session.snapshot()

    assert snapshot["agent"]["memory"] == {
        "preferences": {"tone": "concise"},
        "project": {
            "name": "Pyxis",
            "description": None,
            "metadata": {},
        },
        "scratchpad": {"working_note": "temporary"},
        "persistent": False,
    }


def test_memory_snapshot_redacts_sensitive_fields() -> None:
    memory = SessionMemory()
    memory.set_preference("api_key", "secret-key")
    memory.set_project_context(metadata={"token": "secret-token"})
    memory.set("content", "private note")

    session = Pyxis(agent=Agent(name="navigator", memory=memory)).session()

    snapshot = session.snapshot(redact=True)
    memory_snapshot = snapshot["agent"]["memory"]

    assert memory_snapshot["preferences"]["api_key"] == "[REDACTED]"
    assert memory_snapshot["project"]["metadata"]["token"] == "[REDACTED]"
    assert memory_snapshot["scratchpad"]["content"] == "[REDACTED]"
