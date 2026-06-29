import json

from pyxis import Agent, AgentActionType, CheckpointStatus, MockProvider, Pyxis, tool


def test_session_navigate_runs_agent() -> None:
    agent = Agent(name="navigator", provider=MockProvider(output="On it."))
    session = Pyxis(agent=agent).session()

    result = session.navigate("Summarize this text")

    assert result.output == "On it."
    assert result.decision == "run_agent"
    assert [event.type for event in session.events] == [
        "UserMessageReceived",
        "CompassDecisionMade",
        "ProviderStarted",
        "ProviderDone",
        "AgentActionParsed",
        "AgentResponded",
    ]


def test_session_creates_checkpoint_when_confirmation_is_required() -> None:
    agent = Agent(name="navigator", provider=MockProvider(output="unused"))
    session = Pyxis(agent=agent).session()

    result = session.navigate("send the email", requires_confirmation=True)

    assert result.decision == "request_confirmation"
    assert len(session.checkpoints) == 1
    assert session.checkpoints[0].status == CheckpointStatus.PENDING


def test_pyxis_facade_passes_confirmation_flag() -> None:
    pyxis = Pyxis(agent=Agent(name="navigator", provider=MockProvider(output="unused")))

    result = pyxis.navigate("send the email", requires_confirmation=True)

    assert result.decision == "request_confirmation"


def test_session_control_primitives_can_recreate_navigation_loop() -> None:
    agent = Agent(name="navigator", provider=MockProvider(output="On it."))
    session = Pyxis(agent=agent).session()

    analysis = session.analyze("Summarize this text")
    prompt = session.build_agent_prompt("Summarize this text", analysis)
    assert prompt == "Summarize this text"

    agent_result = session.run_agent(prompt, context={"decision": analysis.decision.type.value})
    action = session.parse_action(agent_result.output)
    output, metadata = session.dispatch_action(action, original_output=agent_result.output)
    result = session.record_agent_response(
        output,
        decision=analysis.decision.type.value,
        metadata=metadata,
    )

    assert action.type == AgentActionType.MESSAGE
    assert result.output == "On it."
    assert result.decision == "run_agent"
    assert result.metadata == {}
    assert [event.type for event in session.events] == [
        "UserMessageReceived",
        "CompassDecisionMade",
        "ProviderStarted",
        "ProviderDone",
        "AgentActionParsed",
        "AgentResponded",
    ]


def test_session_control_primitives_can_dispatch_tool_call() -> None:
    @tool(risk="low", action="summarize")
    def summarize(text: str) -> str:
        return text[:5]

    provider = MockProvider(
        output=json.dumps(
            {
                "type": "tool_call",
                "tool": "summarize",
                "args": {"text": "pyxis-agent"},
            }
        )
    )
    session = Pyxis(agent=Agent(name="navigator", provider=provider, tools=[summarize])).session()

    analysis = session.analyze("summarize")
    agent_result = session.run_agent(
        "summarize",
        context={"decision": analysis.decision.type.value},
    )
    action = session.parse_action(agent_result.output)
    output, metadata = session.dispatch_action(action, original_output=agent_result.output)
    result = session.record_agent_response(
        output,
        decision=analysis.decision.type.value,
        metadata=metadata,
    )

    assert result.output == "pyxis"
    assert result.metadata["agent_action"].type == AgentActionType.TOOL_CALL
    assert result.metadata["tool_result"].output == "pyxis"


def test_checkpoint_can_be_approved() -> None:
    agent = Agent(name="navigator")
    session = Pyxis(agent=agent).session()

    checkpoint = session.checkpoint(
        reason="About to act",
        action="shell_exec",
        summary="Pyxis wants to run a shell command.",
        risk_reason="This may execute local commands.",
        preview="echo hi",
    )
    checkpoint.approve()

    assert checkpoint.approved
    assert checkpoint.to_dict()["summary"] == "Pyxis wants to run a shell command."
    assert checkpoint.to_dict()["risk_reason"] == "This may execute local commands."
    assert checkpoint.to_dict()["preview"] == "echo hi"
    assert checkpoint.to_dict()["options"] == ["approve", "reject"]
