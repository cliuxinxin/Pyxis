from pyxis import tool


def test_tool_decorator_wraps_callable() -> None:
    @tool(risk="medium", action="summarize")
    def summarize(text: str) -> str:
        """Summarize text."""
        return text[:4]

    result = summarize("pyxis")

    assert summarize.name == "summarize"
    assert summarize.description == "Summarize text."
    assert summarize.parameter_schema() == {
        "text": {
            "type": "str",
            "required": True,
        }
    }
    assert result.output == "pyxi"
    assert result.metadata["risk"] == "medium"
