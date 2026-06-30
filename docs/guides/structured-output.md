# Structured Output

Use structured output when an application needs provider text to become a
validated JSON object.

This is useful for product workflows such as signals, briefings, importance
scores, routing decisions, and extraction tasks.

## Run With A Schema

```python
from pyxis import Agent, MockProvider, Pyxis

schema = {
    "type": "object",
    "required": ["importance", "reason"],
    "properties": {
        "importance": {"type": "number"},
        "reason": {"type": "string"},
    },
}

agent = Agent(
    name="scorer",
    provider=MockProvider(output='{"importance": 0.82, "reason": "Fresh signal"}'),
)

session = Pyxis(agent=agent).session()
result = session.structured_run("Score this signal", schema=schema)

if result.valid:
    print(result.output["importance"])
else:
    print(result.errors)
```

`structured_run()` records the user prompt, emits provider lifecycle events,
parses the response as JSON, validates it locally, and records structured output
events.

## Retry Invalid JSON

Set `max_retries` when you want Pyxis to ask the provider to repair invalid
JSON:

```python
result = session.structured_run(
    "Extract a briefing score",
    schema=schema,
    max_retries=1,
)
```

The retry prompt includes the original schema and the local validation errors.
Pyxis does not hide invalid output: if all attempts fail, the returned
`StructuredResult` has `valid=False`, the last `raw_output`, and the collected
`errors`.

## Supported Schema Subset

The helper intentionally supports a small JSON schema subset:

- `type`
- `required`
- `properties`
- `items`
- `enum`

This keeps Pyxis dependency-light and provider-neutral. Applications that need
Pydantic, database constraints, or provider-native JSON schema can layer those
on top of the same session control flow.

## Observability

Structured runs emit:

- `StructuredOutputRequested`
- `StructuredOutputParsed`
- `StructuredOutputValidationFailed`

Use event sinks when a host application needs to persist those events for a Web
UI or audit trail.
