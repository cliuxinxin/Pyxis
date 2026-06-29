# Control Flow Guide

Pyxis is designed to be convenient at the top and programmable underneath.

For common cases, use the high-level API:

```python
result = session.navigate("Plan a controlled research workflow")
```

For advanced cases, you can write the turn loop yourself:

```python
analysis = session.analyze("Plan a controlled research workflow")
prompt = session.build_agent_prompt(
    "Plan a controlled research workflow",
    analysis,
)

if prompt is not None:
    agent_result = session.run_agent(
        prompt,
        context={"decision": analysis.decision.type.value},
    )
    action = session.parse_action(agent_result.output)
    output, metadata = session.dispatch_action(
        action,
        original_output=agent_result.output,
    )
else:
    output = analysis.decision.prompt or "No agent step needed."
    metadata = {"analysis": analysis}

result = session.record_agent_response(
    output,
    decision=analysis.decision.type.value,
    metadata=metadata,
)
```

This gives host applications direct control over prompt construction, provider
calls, action parsing, tool dispatch, and final recording while preserving the
same event log, checkpoints, policies, and snapshots used by `navigate()`.

## Useful Control Points

- `analyze()`: record the user message and get a `CompassAnalysis`.
- `build_agent_prompt()`: turn an analysis into the prompt that should reach the
  provider, or `None` when no provider call is needed.
- `run_agent()`: call the provider with provider lifecycle events.
- `parse_action()`: parse a provider response into the Pyxis action protocol.
- `dispatch_action()`: execute tool calls, stop actions, or message actions.
- `record_agent_response()`: write the final response into dialogue and return a
  `NavigationResult`.

## Why This Shape

The goal is similar to PyTorch's feel: a good default path, but no sealed graph.
You can keep the normal Pyxis safety rails and observability while still writing
your own loop when an application needs custom prompting, routing, retries,
review steps, or UI handoffs.
