from pyxis import (
    Agent,
    Compass,
    CompassDecisionType,
    IntentType,
    MockProvider,
    Pyxis,
)


def test_compass_analysis_captures_intent_goal_and_preferences() -> None:
    analysis = Compass().analyze("请简洁规划一个 research workflow，必须可控")

    assert analysis.decision.type == CompassDecisionType.PROPOSE_PLAN
    assert analysis.intent.type == IntentType.PLAN
    assert analysis.goal is not None
    assert analysis.goal.text == "请简洁规划一个 research workflow，必须可控"
    assert analysis.preferences["tone"] == "concise"
    assert analysis.constraints == ["请简洁规划一个 research workflow，必须可控"]


def test_compass_analysis_clarifies_underspecified_requests() -> None:
    analysis = Compass().analyze("帮我弄一下")

    assert analysis.decision.type == CompassDecisionType.ASK_CLARIFICATION
    assert analysis.intent.needs_clarification
    assert analysis.clarification is not None
    assert analysis.clarification.question == "Can you clarify the outcome you want?"


def test_session_records_structured_dialogue_analysis() -> None:
    session = Pyxis(agent=Agent(name="navigator")).session()

    result = session.navigate("帮我弄一下")

    assert result.decision == "ask_clarification"
    assert session.dialogue.intent is not None
    assert session.dialogue.intent.needs_clarification
    assert session.dialogue.clarifications
    assert session.dialogue.open_questions == ["Can you clarify the outcome you want?"]


def test_agent_applies_response_style_to_provider_output() -> None:
    agent = Agent(name="navigator", provider=MockProvider(output="  steady answer  "))

    result = agent.run("Where next?")

    assert result.output == "steady answer"


def test_agent_response_style_handles_empty_provider_output() -> None:
    agent = Agent(name="navigator", provider=MockProvider(output="  "))

    result = agent.run("Where next?")

    assert result.output == "I need a little more context before I can help well."
