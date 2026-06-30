"""Tool wrappers for Python callables."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin

from pyxis.errors import ToolExecutionError, ToolValidationError
from pyxis.results import ToolResult
from pyxis.serialization import to_jsonable
from pyxis.types import JsonDict, RiskLevel


@dataclass(frozen=True)
class ToolCall:
    """A pending or executed tool invocation."""

    name: str
    args: tuple[Any, ...] = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)
    risk: RiskLevel = "low"
    action: str = "tool_call"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "args": list(self.args),
            "kwargs": self.kwargs,
            "risk": self.risk,
            "action": self.action,
        }


@dataclass(frozen=True)
class Tool:
    """A callable capability exposed to an agent."""

    name: str
    fn: Callable[..., Any]
    description: str = ""
    risk: RiskLevel = "low"
    action: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def manifest(self) -> JsonDict:
        """Return the tool information exposed to an agent."""

        return {
            "name": self.name,
            "description": self.description,
            "risk": self.risk,
            "action": self.action or "tool_call",
            "parameters": self.parameter_schema(),
        }

    def parameter_schema(self) -> JsonDict:
        """Return a simple schema derived from the callable signature."""

        signature = inspect.signature(self.fn)
        parameters: dict[str, JsonDict] = {}

        for name, parameter in signature.parameters.items():
            if parameter.kind in {
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            }:
                continue

            entry: JsonDict = {
                "type": _annotation_name(parameter.annotation),
                "required": parameter.default is inspect.Parameter.empty,
            }
            if parameter.default is not inspect.Parameter.empty:
                entry["default"] = to_jsonable(parameter.default)
            parameters[name] = entry

        return parameters

    def validate_arguments(self, *args: Any, **kwargs: Any) -> None:
        """Validate a tool call against the callable signature and annotations."""

        signature = inspect.signature(self.fn)
        try:
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
        except TypeError as exc:
            raise ToolValidationError(
                f"Tool {self.name!r} arguments are invalid: {exc}"
            ) from exc

        for name, value in bound.arguments.items():
            parameter = signature.parameters[name]
            annotation = parameter.annotation
            if not _matches_annotation(value, annotation):
                expected = _annotation_name(annotation)
                actual = type(value).__name__
                raise ToolValidationError(
                    f"Tool {self.name!r} argument {name!r} expected {expected}, "
                    f"got {actual}."
                )

    @property
    def is_async(self) -> bool:
        """Return whether the underlying tool callable is asynchronous."""

        return inspect.iscoroutinefunction(self.fn)

    def __call__(self, *args: Any, **kwargs: Any) -> ToolResult:
        if self.is_async:
            raise ToolExecutionError(
                f"Tool {self.name!r} is async. Use acall_tool() or Tool.acall()."
            )
        self.validate_arguments(*args, **kwargs)
        try:
            output = self.fn(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - exact exception is user code.
            raise ToolExecutionError(f"Tool {self.name!r} failed: {exc}") from exc
        return ToolResult(
            name=self.name,
            output=output,
            requires_confirmation=False,
            metadata={"risk": self.risk, **self.metadata},
        )

    async def acall(self, *args: Any, **kwargs: Any) -> ToolResult:
        """Execute a sync or async tool and return a ToolResult."""

        self.validate_arguments(*args, **kwargs)
        try:
            output = self.fn(*args, **kwargs)
            if inspect.isawaitable(output):
                output = await output
        except Exception as exc:  # pragma: no cover - exact exception is user code.
            raise ToolExecutionError(f"Tool {self.name!r} failed: {exc}") from exc
        return ToolResult(
            name=self.name,
            output=output,
            requires_confirmation=False,
            metadata={"risk": self.risk, **self.metadata},
        )


def tool(
    fn: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    risk: RiskLevel = "low",
    action: str | None = None,
    **metadata: Any,
):
    """Decorate a Python callable as a Pyxis tool."""

    def decorate(func: Callable[..., Any]) -> Tool:
        return Tool(
            name=name or func.__name__,
            fn=func,
            description=description or (func.__doc__ or "").strip(),
            risk=risk,
            action=action,
            metadata=metadata,
        )

    if fn is None:
        return decorate

    return decorate(fn)


def _annotation_name(annotation: Any) -> str:
    if annotation is inspect.Signature.empty:
        return "Any"
    if isinstance(annotation, str):
        return annotation
    if getattr(annotation, "__module__", "") == "builtins":
        return getattr(annotation, "__name__", repr(annotation))

    text = str(annotation)
    return text.replace("typing.", "")


def _matches_annotation(value: Any, annotation: Any) -> bool:
    if annotation is inspect.Signature.empty or annotation is Any:
        return True

    if isinstance(annotation, str):
        return True

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin in {Union, UnionType}:
        return any(_matches_annotation(value, option) for option in args)

    if origin is Literal:
        return value in args

    if origin is not None:
        if origin in {list, dict, tuple, set}:
            return isinstance(value, origin)
        return True

    if annotation is bool:
        return isinstance(value, bool)
    if annotation is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if annotation is float:
        return isinstance(value, int | float) and not isinstance(value, bool)
    if annotation in {str, bytes, dict, list, tuple, set}:
        return isinstance(value, annotation)

    if isinstance(annotation, type):
        return isinstance(value, annotation)

    return True
