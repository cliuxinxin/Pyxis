import pytest

from pyxis import (
    EVENT_SCHEMA_VERSION,
    EVENT_SCHEMAS,
    Agent,
    Event,
    EventLog,
    EventSinkError,
    EventType,
    InMemoryEventSink,
    MockProvider,
    NullEventSink,
    Pyxis,
    Workflow,
)


def test_event_log_validates_known_event_payloads() -> None:
    events = EventLog()

    with pytest.raises(ValueError, match="content"):
        events.emit(EventType.USER_MESSAGE_RECEIVED)

    event = events.emit(EventType.USER_MESSAGE_RECEIVED, content="hello")

    assert event.type == "UserMessageReceived"
    assert event.schema_version == EVENT_SCHEMA_VERSION
    assert event.to_dict()["schema_version"] == EVENT_SCHEMA_VERSION


def test_event_log_writes_emitted_events_to_sink() -> None:
    sink = InMemoryEventSink()
    events = EventLog(sinks=[sink])

    event = events.emit("CustomEvent", value=1)

    assert sink.all() == [event]
    assert sink.to_list() == [event.to_dict()]


def test_event_log_writes_to_multiple_sinks() -> None:
    first = InMemoryEventSink()
    second = InMemoryEventSink()
    events = EventLog(sinks=[first, second])

    event = events.emit("CustomEvent", value=1)

    assert first.all() == [event]
    assert second.all() == [event]


def test_null_event_sink_discards_events() -> None:
    events = EventLog(sinks=[NullEventSink()])

    event = events.emit("CustomEvent", value=1)

    assert events.all() == [event]


def test_event_log_wraps_sink_failures() -> None:
    class BrokenSink:
        def write(self, event):
            raise RuntimeError("database unavailable")

    events = EventLog(sinks=[BrokenSink()])

    with pytest.raises(EventSinkError, match="database unavailable"):
        events.emit("CustomEvent", value=1)


def test_event_log_append_does_not_notify_sinks_by_default() -> None:
    sink = InMemoryEventSink()
    events = EventLog(sinks=[sink])
    event = Event(type="RestoredEvent", payload={"value": 1})

    events.append(event)

    assert events.all() == [event]
    assert sink.all() == []


def test_event_log_append_can_notify_sinks() -> None:
    sink = InMemoryEventSink()
    events = EventLog(sinks=[sink])
    event = Event(type="ImportedEvent", payload={"value": 1})

    events.append(event, notify=True)

    assert sink.all() == [event]


def test_event_schemas_include_provider_tool_checkpoint_and_workflow_contracts() -> None:
    assert EVENT_SCHEMAS["ProviderStarted"].required == ("agent", "provider", "mode")
    assert EVENT_SCHEMAS["ToolValidationFailed"].required == ("tool", "error")
    assert EVENT_SCHEMAS["CheckpointResumed"].required == ("checkpoint_id",)
    assert EVENT_SCHEMAS["StructuredOutputRequested"].required == ("schema",)
    assert EVENT_SCHEMAS["StructuredOutputParsed"].required == ("valid",)
    assert EVENT_SCHEMAS["StructuredOutputValidationFailed"].required == ("errors",)
    assert EVENT_SCHEMAS["WorkflowStepCompleted"].required == (
        "workflow",
        "step",
        "index",
        "kind",
    )


def test_session_records_provider_started_and_done_events() -> None:
    session = Pyxis(agent=Agent(name="navigator", provider=MockProvider(output="hello"))).session()

    session.navigate("say hello")

    events = [(event.type, event.payload) for event in session.events]
    assert (
        "ProviderStarted",
        {"agent": "navigator", "provider": "MockProvider", "mode": "complete"},
    ) in events
    assert any(
        event_type == "ProviderDone"
        and payload["agent"] == "navigator"
        and payload["provider"] == "MockProvider"
        and payload["mode"] == "complete"
        and payload["finish_reason"] == "stop"
        for event_type, payload in events
    )


def test_session_records_provider_error_events() -> None:
    class BrokenProvider:
        def complete(self, request):
            raise RuntimeError("provider unavailable")

    session = Pyxis(agent=Agent(name="navigator", provider=BrokenProvider())).session()

    with pytest.raises(RuntimeError, match="provider unavailable"):
        session.navigate("say hello")

    provider_error = next(event for event in session.events if event.type == "ProviderError")
    assert provider_error.payload == {
        "agent": "navigator",
        "provider": "BrokenProvider",
        "mode": "complete",
        "error": "RuntimeError",
        "message": "provider unavailable",
    }


def test_session_records_workflow_step_events() -> None:
    workflow = Workflow("numbers").step("add-one", lambda value: value + 1)
    session = Pyxis(agent=Agent(name="navigator")).session()

    session.run(workflow, 3)

    event_types = [event.type for event in session.events]
    assert event_types == [
        "WorkflowStarted",
        "WorkflowStepStarted",
        "WorkflowStepCompleted",
        "WorkflowCompleted",
    ]
    completed = session.events.all()[2]
    assert completed.payload == {
        "workflow": "numbers",
        "step": "add-one",
        "index": 0,
        "kind": "callable",
    }


def test_session_records_workflow_step_failure() -> None:
    def fail(value):
        raise ValueError(f"bad {value}")

    workflow = Workflow("numbers").step("fail", fail)
    session = Pyxis(agent=Agent(name="navigator")).session()

    with pytest.raises(ValueError, match="bad 3"):
        session.run(workflow, 3)

    failure = session.events.all()[-1]
    assert failure.type == "WorkflowStepFailed"
    assert failure.payload == {
        "workflow": "numbers",
        "step": "fail",
        "index": 0,
        "kind": "callable",
        "error": "ValueError",
        "message": "bad 3",
    }
