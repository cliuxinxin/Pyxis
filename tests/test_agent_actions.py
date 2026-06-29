import json

from pyxis import Agent, AgentActionType, CheckpointStatus, MockProvider, Pyxis, tool
from pyxis.actions import parse_agent_action
from pyxis.errors import ToolNotFound


def test_parse_agent_action_reads_tool_call_kwargs() -> None:
    action = parse_agent_action(
        json.dumps(
            {
                "type": "tool_call",
                "tool": "summarize",
                "args": {"text": "pyxis"},
            }
        )
    )

    assert action.type == AgentActionType.TOOL_CALL
    assert action.tool == "summarize"
    assert action.kwargs == {"text": "pyxis"}


def test_parse_agent_action_treats_malformed_json_as_message() -> None:
    action = parse_agent_action('{"type": "tool_call"')

    assert action.type == AgentActionType.MESSAGE
    assert action.content == '{"type": "tool_call"'


def test_parse_agent_action_reads_json_code_block() -> None:
    action = parse_agent_action(
        """
        Here is the action:

        ```json
        {"type":"tool_call","tool":"summarize","args":{"text":"pyxis"}}
        ```
        """
    )

    assert action.type == AgentActionType.TOOL_CALL
    assert action.tool == "summarize"
    assert action.kwargs == {"text": "pyxis"}


def test_parse_agent_action_reads_json_with_surrounding_text() -> None:
    action = parse_agent_action(
        'I will use a tool: {"type":"tool_call","tool":"summarize","args":{"text":"pyxis"}}'
    )

    assert action.type == AgentActionType.TOOL_CALL
    assert action.tool == "summarize"


def test_parse_agent_action_ignores_malformed_json_code_block() -> None:
    text = "```json\n{\"type\":\"tool_call\"\n```"

    action = parse_agent_action(text)

    assert action.type == AgentActionType.MESSAGE
    assert action.content == text


def test_navigate_preserves_plain_agent_message() -> None:
    agent = Agent(name="navigator", provider=MockProvider(output="Plain answer."))
    session = Pyxis(agent=agent).session()

    result = session.navigate("hello")

    assert result.output == "Plain answer."
    assert result.metadata == {}


def test_navigate_executes_low_risk_tool_call() -> None:
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
    agent = Agent(name="navigator", provider=provider, tools=[summarize])
    session = Pyxis(agent=agent).session()

    result = session.navigate("summarize")

    assert result.output == "pyxis"
    assert result.metadata["agent_action"].type == AgentActionType.TOOL_CALL
    assert result.metadata["tool_result"].output == "pyxis"


def test_navigate_pauses_high_risk_tool_call() -> None:
    calls: list[str] = []

    @tool(risk="high", action="file_write")
    def write_file(path: str) -> str:
        calls.append(path)
        return path

    provider = MockProvider(
        output=json.dumps(
            {
                "type": "tool_call",
                "tool": "write_file",
                "args": {"path": "demo.txt"},
            }
        )
    )
    agent = Agent(name="navigator", provider=provider, tools=[write_file])
    session = Pyxis(agent=agent).session()

    result = session.navigate("write file")

    assert result.output.startswith("Confirmation required")
    assert result.metadata["tool_result"].requires_confirmation is True
    assert session.checkpoints[0].status == CheckpointStatus.PENDING
    assert calls == []


def test_navigate_unknown_tool_raises_clear_error() -> None:
    provider = MockProvider(
        output=json.dumps(
            {
                "type": "tool_call",
                "tool": "missing",
                "args": {},
            }
        )
    )
    session = Pyxis(agent=Agent(name="navigator", provider=provider)).session()

    try:
        session.navigate("use missing tool")
    except ToolNotFound as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("ToolNotFound was not raised")
