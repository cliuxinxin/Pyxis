from pyxis import Agent, MockProvider, tool


def test_agent_without_tools_keeps_original_instructions() -> None:
    provider = MockProvider(output="ok")
    agent = Agent(name="navigator", instructions="Be calm.", provider=provider)

    agent.run("hello")

    assert provider.requests[0].instructions == "Be calm."


def test_agent_injects_tool_manifest_into_instructions() -> None:
    @tool(risk="high", action="file_write")
    def write_file(path: str, content: str) -> str:
        """Write content to a file."""
        return path

    provider = MockProvider(output="ok")
    agent = Agent(
        name="navigator",
        instructions="Be calm.",
        provider=provider,
        tools=[write_file],
    )

    agent.run("hello")

    instructions = provider.requests[0].instructions
    assert "Be calm." in instructions
    assert "controlled action protocol" in instructions
    assert '{"type":"tool_call","tool":"tool_name","args":{"arg_name":"value"}}' in instructions
    assert "write_file: Write content to a file. (risk=high, action=file_write" in instructions
    assert '"path":{"required":true,"type":"str"}' in instructions
    assert '"content":{"required":true,"type":"str"}' in instructions


def test_tool_manifest_uses_default_action() -> None:
    @tool(risk="low")
    def summarize(text: str) -> str:
        return text[:5]

    assert summarize.manifest() == {
        "name": "summarize",
        "description": "",
        "risk": "low",
        "action": "tool_call",
        "parameters": {
            "text": {
                "type": "str",
                "required": True,
            }
        },
    }


def test_tool_manifest_includes_parameter_defaults() -> None:
    @tool(risk="low", action="search")
    def search(query: str, limit: int = 5) -> str:
        return query[:limit]

    assert search.manifest()["parameters"] == {
        "query": {
            "type": "str",
            "required": True,
        },
        "limit": {
            "type": "int",
            "required": False,
            "default": 5,
        },
    }
