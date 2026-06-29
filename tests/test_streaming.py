import json

from pyxis import Agent, MockProvider, Pyxis, tool


def test_session_stream_yields_start_result_done() -> None:
    session = Pyxis(agent=Agent(name="navigator", provider=MockProvider(output="hello"))).session()

    events = list(session.stream("say hello"))

    assert [event.type for event in events] == ["start", "result", "done"]
    assert events[0].data["input"] == "say hello"
    assert events[1].data["output"] == "hello"
    assert events[2].data["output"] == "hello"


def test_session_stream_yields_checkpoint_for_paused_tool_call() -> None:
    @tool(risk="high", action="file_write")
    def write_file(path: str) -> str:
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
    session = Pyxis(agent=Agent(name="navigator", provider=provider, tools=[write_file])).session()

    events = list(session.stream("write file"))

    assert [event.type for event in events] == ["start", "result", "checkpoint", "done"]
    assert events[2].data["tool"] == "write_file"
    assert events[2].data["checkpoint"]["status"] == "pending"
