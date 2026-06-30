"""Structured output helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from pyxis.types import JsonDict


@dataclass(frozen=True)
class StructuredResult:
    """A parsed and locally validated structured provider response."""

    output: dict[str, Any] = field(default_factory=dict)
    raw_output: str = ""
    valid: bool = False
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def structured_prompt(prompt: str, schema: JsonDict) -> str:
    """Build a provider prompt that asks for JSON matching a schema."""

    schema_text = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True)
    return (
        f"{prompt}\n\n"
        "Return only valid JSON. Do not wrap it in Markdown. "
        "The JSON must match this schema:\n"
        f"{schema_text}"
    )


def retry_structured_prompt(prompt: str, schema: JsonDict, errors: list[str]) -> str:
    """Build a repair prompt for invalid structured output."""

    formatted_errors = "\n".join(f"- {error}" for error in errors)
    return (
        f"{structured_prompt(prompt, schema)}\n\n"
        "The previous response did not match the schema. Fix these issues and "
        "return only corrected JSON:\n"
        f"{formatted_errors}"
    )


def parse_structured_output(raw_output: str, schema: JsonDict) -> StructuredResult:
    """Parse and validate a provider response against a small JSON schema subset."""

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        return StructuredResult(
            raw_output=raw_output,
            errors=[f"Response was not valid JSON: {exc.msg}."],
        )

    errors = validate_json_schema(parsed, schema)
    if not isinstance(parsed, dict):
        errors.insert(0, "Response root must be an object.")
        output: dict[str, Any] = {}
    else:
        output = parsed

    return StructuredResult(
        output=output,
        raw_output=raw_output,
        valid=not errors,
        errors=errors,
    )


def validate_json_schema(value: Any, schema: JsonDict, *, path: str = "$") -> list[str]:
    """Validate value against a lightweight JSON schema subset."""

    errors: list[str] = []

    if "enum" in schema:
        options = schema["enum"]
        if isinstance(options, list) and value not in options:
            errors.append(f"{path} must be one of {options!r}.")

    schema_type = schema.get("type")
    if schema_type is not None and not _matches_type(value, schema_type):
        errors.append(f"{path} must be {_format_type(schema_type)}, got {type(value).__name__}.")
        return errors

    if schema_type == "object" or (
        schema_type is None and isinstance(value, dict) and "properties" in schema
    ):
        if not isinstance(value, dict):
            errors.append(f"{path} must be object, got {type(value).__name__}.")
            return errors

        required = schema.get("required", [])
        if isinstance(required, list):
            for key in required:
                if isinstance(key, str) and key not in value:
                    errors.append(f"{path}.{key} is required.")

        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, child_schema in properties.items():
                if key not in value or not isinstance(child_schema, dict):
                    continue
                errors.extend(
                    validate_json_schema(value[key], child_schema, path=f"{path}.{key}")
                )

    if schema_type == "array" or (
        schema_type is None and isinstance(value, list) and "items" in schema
    ):
        if not isinstance(value, list):
            errors.append(f"{path} must be array, got {type(value).__name__}.")
            return errors

        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(validate_json_schema(item, item_schema, path=f"{path}[{index}]"))

    return errors


def _matches_type(value: Any, schema_type: Any) -> bool:
    if isinstance(schema_type, list):
        return any(_matches_type(value, option) for option in schema_type)

    if schema_type == "object":
        return isinstance(value, dict)
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "null":
        return value is None
    return True


def _format_type(schema_type: Any) -> str:
    if isinstance(schema_type, list):
        return " or ".join(str(option) for option in schema_type)
    return str(schema_type)
