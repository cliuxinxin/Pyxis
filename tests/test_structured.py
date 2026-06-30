from pyxis import Agent, CompletionResult, MockProvider, Pyxis


SIGNAL_SCHEMA = {
    "type": "object",
    "required": ["importance", "reason"],
    "properties": {
        "importance": {"type": "number"},
        "reason": {"type": "string"},
    },
}


class SequenceProvider:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        return CompletionResult(output=self.outputs.pop(0))


def test_structured_run_returns_valid_json_object() -> None:
    session = Pyxis(
        agent=Agent(
            name="navigator",
            provider=MockProvider(output='{"importance": 0.82, "reason": "Fresh signal"}'),
        )
    ).session()

    result = session.structured_run("Score this signal", schema=SIGNAL_SCHEMA)

    assert result.valid is True
    assert result.output == {"importance": 0.82, "reason": "Fresh signal"}
    assert result.errors == []
    assert result.metadata["attempts"] == 1


def test_structured_run_reports_invalid_json() -> None:
    session = Pyxis(agent=Agent(name="navigator", provider=MockProvider(output="not json"))).session()

    result = session.structured_run("Score this signal", schema=SIGNAL_SCHEMA)

    assert result.valid is False
    assert result.output == {}
    assert result.raw_output == "not json"
    assert "not valid JSON" in result.errors[0]


def test_structured_run_reports_missing_required_fields() -> None:
    session = Pyxis(
        agent=Agent(name="navigator", provider=MockProvider(output='{"importance": 0.3}'))
    ).session()

    result = session.structured_run("Score this signal", schema=SIGNAL_SCHEMA)

    assert result.valid is False
    assert "$.reason is required." in result.errors


def test_structured_run_reports_type_errors() -> None:
    session = Pyxis(
        agent=Agent(
            name="navigator",
            provider=MockProvider(output='{"importance": "high", "reason": "Relevant"}'),
        )
    ).session()

    result = session.structured_run("Score this signal", schema=SIGNAL_SCHEMA)

    assert result.valid is False
    assert "$.importance must be number, got str." in result.errors


def test_structured_run_validates_array_items() -> None:
    schema = {
        "type": "object",
        "required": ["topics"],
        "properties": {
            "topics": {
                "type": "array",
                "items": {"type": "string"},
            }
        },
    }
    session = Pyxis(
        agent=Agent(name="navigator", provider=MockProvider(output='{"topics": ["ai", 3]}'))
    ).session()

    result = session.structured_run("Extract topics", schema=schema)

    assert result.valid is False
    assert "$.topics[1] must be string, got int." in result.errors


def test_structured_run_validates_enum_values() -> None:
    schema = {
        "type": "object",
        "required": ["priority"],
        "properties": {
            "priority": {"type": "string", "enum": ["low", "medium", "high"]},
        },
    }
    session = Pyxis(
        agent=Agent(name="navigator", provider=MockProvider(output='{"priority": "urgent"}'))
    ).session()

    result = session.structured_run("Classify priority", schema=schema)

    assert result.valid is False
    assert "$.priority must be one of ['low', 'medium', 'high']." in result.errors


def test_structured_run_retries_until_valid() -> None:
    provider = SequenceProvider(
        [
            '{"importance": "high"}',
            '{"importance": 0.91, "reason": "Matches the watchlist"}',
        ]
    )
    session = Pyxis(agent=Agent(name="navigator", provider=provider)).session()

    result = session.structured_run("Score this signal", schema=SIGNAL_SCHEMA, max_retries=1)

    assert result.valid is True
    assert result.output == {"importance": 0.91, "reason": "Matches the watchlist"}
    assert result.metadata["attempts"] == 2
    assert len(provider.requests) == 2
    assert "previous response did not match" in provider.requests[1].prompt


def test_structured_run_records_structured_events() -> None:
    session = Pyxis(
        agent=Agent(
            name="navigator",
            provider=MockProvider(output='{"importance": 0.82, "reason": "Fresh signal"}'),
        )
    ).session()

    session.structured_run("Score this signal", schema=SIGNAL_SCHEMA)

    event_types = [event.type for event in session.events]
    assert "StructuredOutputRequested" in event_types
    assert "StructuredOutputParsed" in event_types
    assert "StructuredOutputValidationFailed" not in event_types


def test_structured_run_records_validation_failure_events() -> None:
    session = Pyxis(agent=Agent(name="navigator", provider=MockProvider(output="not json"))).session()

    session.structured_run("Score this signal", schema=SIGNAL_SCHEMA)

    event_types = [event.type for event in session.events]
    assert "StructuredOutputRequested" in event_types
    assert "StructuredOutputParsed" in event_types
    assert "StructuredOutputValidationFailed" in event_types
