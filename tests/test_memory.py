from pyxis import Agent, InMemoryStore, MemoryItem, NoMemoryStore, Pyxis, SessionMemory


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


def test_session_memory_can_snapshot_long_term_store() -> None:
    store = InMemoryStore()
    store.set("user", "watchlist", ["agents"])
    memory = SessionMemory(store=store)
    session = Pyxis(agent=Agent(name="navigator", memory=memory)).session()

    snapshot = session.snapshot()

    assert snapshot["agent"]["memory"]["store"]["items"][0]["namespace"] == "user"
    assert snapshot["agent"]["memory"]["store"]["items"][0]["key"] == "watchlist"
    assert snapshot["agent"]["memory"]["store"]["items"][0]["value"] == ["agents"]


def test_no_memory_store_returns_defaults_and_empty_snapshot() -> None:
    store = NoMemoryStore()

    store.set("user", "topic", "ai")
    store.delete("user", "topic")

    assert store.get("user", "topic", default="missing") == "missing"
    assert store.list("user") == []
    assert store.to_dict() == {"items": [], "persistent": False}


def test_in_memory_store_keeps_namespaces_isolated() -> None:
    store = InMemoryStore()

    store.set("user", "topic", "agents")
    store.set("project", "topic", "release")

    assert store.get("user", "topic") == "agents"
    assert store.get("project", "topic") == "release"
    assert [item.key for item in store.list("user")] == ["topic"]


def test_in_memory_store_updates_and_deletes_items() -> None:
    store = InMemoryStore()

    store.set("user", "topic", "agents", metadata={"source": "feedback"})
    first = store.list("user")[0]
    store.set("user", "topic", "briefings", metadata={"source": "preference"})
    updated = store.list("user")[0]

    assert store.get("user", "topic") == "briefings"
    assert updated.created_at == first.created_at
    assert updated.updated_at is not None
    assert updated.metadata == {"source": "preference"}

    store.delete("user", "topic")

    assert store.get("user", "topic") is None
    assert store.list("user") == []


def test_memory_item_and_store_are_json_safe() -> None:
    item = MemoryItem(
        namespace="user",
        key="weights",
        value={"signals": [1, 2]},
        metadata={"kind": "preference"},
    )
    store = InMemoryStore(items=[item])

    assert item.to_dict()["value"] == {"signals": [1, 2]}
    assert item.to_dict()["created_at"].endswith("+00:00")
    assert store.to_dict()["items"][0]["metadata"] == {"kind": "preference"}
