# Tool Actions

Tools are Python callables exposed to an agent with risk and action metadata.
Pyxis uses that metadata to decide whether a tool can run directly or needs a
checkpoint.

```python
from pyxis import tool

@tool(risk="high", action="file_write")
def write_file(path: str, content: str) -> str:
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)
    return path
```

## Tool Metadata

- `name`: function name by default.
- `description`: function docstring.
- `risk`: `low`, `medium`, or `high`.
- `action`: domain action, such as `summarize`, `shell_exec`, or `file_write`.
- `parameters`: a signature-derived schema used in the tool manifest.

## Agent Action Protocol

Agents can request a tool call by returning JSON:

```json
{
  "type": "tool_call",
  "tool": "summarize",
  "args": {
    "text": "Pyxis keeps human control visible."
  }
}
```

`Session.navigate()` parses this action after the provider responds. Low-risk
tools run immediately. High-risk tools pause with a checkpoint.

## Why Actions Matter

Risk alone is not enough. The `action` field gives policy and UI code a stable
surface to describe what is about to happen:

```text
Action: file_write
Reason: This is a high-risk file_write action.
Preview: write_file('notes.txt')
```
