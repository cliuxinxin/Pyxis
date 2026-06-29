from pyxis import Agent, CheckpointStatus, MockProvider, Pyxis


def test_session_navigate_runs_agent() -> None:
    agent = Agent(name="navigator", provider=MockProvider(output="On it."))
    session = Pyxis(agent=agent).session()

    result = session.navigate("Summarize this text")

    assert result.output == "On it."
    assert result.decision == "run_agent"
    assert [event.type for event in session.events] == [
        "UserMessageReceived",
        "CompassDecisionMade",
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


def test_checkpoint_can_be_approved() -> None:
    agent = Agent(name="navigator")
    session = Pyxis(agent=agent).session()

    checkpoint = session.checkpoint(reason="About to act", action="shell_exec")
    checkpoint.approve()

    assert checkpoint.approved
