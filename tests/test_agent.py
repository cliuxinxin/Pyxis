from pyxis import Agent, MockProvider


def test_agent_runs_with_provider() -> None:
    provider = MockProvider(output="steady answer")
    agent = Agent(name="navigator", instructions="Be concise.", provider=provider)

    result = agent.run("Where next?")

    assert result.output == "steady answer"
    assert provider.requests[0].prompt == "Where next?"
    assert provider.requests[0].instructions == "Be concise."
