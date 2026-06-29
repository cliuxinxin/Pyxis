from typing import Literal

import pytest

from pyxis import ToolValidationError, tool


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


def test_tool_validation_rejects_missing_required_argument() -> None:
    @tool
    def summarize(text: str) -> str:
        return text

    with pytest.raises(ToolValidationError, match="missing a required argument"):
        summarize()


def test_tool_validation_rejects_unexpected_argument() -> None:
    @tool
    def summarize(text: str) -> str:
        return text

    with pytest.raises(ToolValidationError, match="unexpected keyword argument"):
        summarize(text="hello", extra=True)


def test_tool_validation_rejects_wrong_annotation_type() -> None:
    @tool
    def repeat(text: str, count: int) -> str:
        return text * count

    with pytest.raises(ToolValidationError, match="argument 'count' expected int"):
        repeat("ha", "2")


def test_tool_validation_allows_defaults_and_literal_values() -> None:
    @tool
    def search(query: str, limit: int = 5, mode: Literal["quick", "deep"] = "quick") -> str:
        return f"{query}:{limit}:{mode}"

    result = search("pyxis")

    assert result.output == "pyxis:5:quick"


def test_tool_validation_rejects_invalid_literal_value() -> None:
    @tool
    def search(query: str, mode: Literal["quick", "deep"] = "quick") -> str:
        return f"{query}:{mode}"

    with pytest.raises(ToolValidationError, match="argument 'mode' expected Literal"):
        search("pyxis", mode="slow")
