import pytest

from pyxis import Agent, CompletionResult, Pyxis, ToolExecutionError, Workflow, tool


@pytest.fixture
def anyio_backend():
    return "asyncio"


class AsyncProvider:
    def __init__(self, output: str) -> None:
        self.output = output
        self.requests = []

    async def acomplete(self, request):
        self.requests.append(request)
        return CompletionResult(
            output=self.output,
            metadata={"finish_reason": "stop"},
            finish_reason="stop",
        )

    def complete(self, request):
        raise AssertionError("sync complete should not be called")


@pytest.mark.anyio
async def test_agent_arun_uses_async_provider() -> None:
    provider = AsyncProvider(" async answer ")
    agent = Agent(name="navigator", provider=provider)

    result = await agent.arun("hello")

    assert result.output == "async answer"
    assert provider.requests[0].prompt == "hello"


@pytest.mark.anyio
async def test_session_arun_agent_records_provider_events() -> None:
    provider = AsyncProvider("hello")
    session = Pyxis(agent=Agent(name="navigator", provider=provider)).session()

    result = await session.arun_agent("hello")

    assert result.output == "hello"
    assert [event.type for event in session.events] == ["ProviderStarted", "ProviderDone"]


@pytest.mark.anyio
async def test_session_acall_tool_executes_async_tool() -> None:
    @tool
    async def fetch_title(url: str) -> str:
        return f"title:{url}"

    session = Pyxis(agent=Agent(name="navigator", tools=[fetch_title])).session()

    result = await session.acall_tool("fetch_title", "https://example.com")

    assert result.output == "title:https://example.com"
    assert [event.type for event in session.events] == [
        "ToolCallRequested",
        "ToolCallCompleted",
    ]


@pytest.mark.anyio
async def test_session_acall_tool_can_execute_sync_tool() -> None:
    @tool
    def uppercase(text: str) -> str:
        return text.upper()

    session = Pyxis(agent=Agent(name="navigator", tools=[uppercase])).session()

    result = await session.acall_tool("uppercase", "pyxis")

    assert result.output == "PYXIS"


def test_session_call_tool_rejects_async_tool() -> None:
    @tool
    async def fetch_title(url: str) -> str:
        return f"title:{url}"

    session = Pyxis(agent=Agent(name="navigator", tools=[fetch_title])).session()

    with pytest.raises(ToolExecutionError, match="Use acall_tool"):
        session.call_tool("fetch_title", "https://example.com")


@pytest.mark.anyio
async def test_session_aresume_checkpoint_executes_async_tool_after_approval() -> None:
    @tool(risk="high", action="network_fetch")
    async def fetch_url(url: str) -> str:
        return f"body:{url}"

    session = Pyxis(agent=Agent(name="navigator", tools=[fetch_url])).session()

    paused = await session.acall_tool("fetch_url", "https://example.com")
    assert paused.requires_confirmation is True

    session.approve_checkpoint(paused.checkpoint.id)
    result = await session.aresume_checkpoint(paused.checkpoint.id)

    assert result.output == "body:https://example.com"
    assert [event.type for event in session.events] == [
        "ToolCallRequested",
        "CheckpointCreated",
        "ToolCallPaused",
        "CheckpointApproved",
        "CheckpointResumed",
        "ToolCallCompleted",
    ]


@pytest.mark.anyio
async def test_session_arun_executes_async_workflow_steps() -> None:
    async def fetch(value: str) -> str:
        return f"{value}:fetched"

    workflow = Workflow("collect").step("fetch", fetch).step("parse", lambda value: value.upper())
    session = Pyxis(agent=Agent(name="navigator")).session()

    result = await session.arun(workflow, "signal")

    assert result.output == "SIGNAL:FETCHED"
    assert result.steps == ["fetch", "parse"]
    assert [event.type for event in session.events] == [
        "WorkflowStarted",
        "WorkflowStepStarted",
        "WorkflowStepCompleted",
        "WorkflowStepStarted",
        "WorkflowStepCompleted",
        "WorkflowCompleted",
    ]


def test_session_run_rejects_async_workflow_step() -> None:
    async def fetch(value: str) -> str:
        return value

    workflow = Workflow("collect").step("fetch", fetch)
    session = Pyxis(agent=Agent(name="navigator")).session()

    with pytest.raises(TypeError, match="Use Workflow.arun"):
        session.run(workflow, "signal")

    assert session.events.all()[-1].type == "WorkflowStepFailed"


@pytest.mark.anyio
async def test_session_aresume_workflow_continues_after_checkpoint() -> None:
    async def finish(value: str) -> str:
        return f"{value}:done"

    workflow = Workflow("collect").checkpoint("Review input.").step("finish", finish)
    session = Pyxis(agent=Agent(name="navigator")).session()

    paused = await session.arun(workflow, "signal")
    assert paused.paused is True

    session.approve_checkpoint(paused.checkpoint.id)
    result = await session.aresume_workflow(paused.checkpoint.id)

    assert result.output == "signal:done"
    assert result.steps == ["finish"]
    assert "WorkflowResumed" in [event.type for event in session.events]


@pytest.mark.anyio
async def test_session_arun_records_workflow_step_failures() -> None:
    async def fail(value: str) -> str:
        raise RuntimeError("fetch failed")

    workflow = Workflow("collect").step("fetch", fail)
    session = Pyxis(agent=Agent(name="navigator")).session()

    with pytest.raises(RuntimeError, match="fetch failed"):
        await session.arun(workflow, "signal")

    failure = session.events.all()[-1]
    assert failure.type == "WorkflowStepFailed"
    assert failure.payload["error"] == "RuntimeError"
