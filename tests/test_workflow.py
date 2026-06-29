import pytest

from pyxis import Agent, CheckpointStatus, Pyxis, Workflow
from pyxis.errors import CheckpointNotApproved, CheckpointRejected


def test_workflow_runs_steps_in_order() -> None:
    workflow = (
        Workflow("numbers")
        .step("add-one", lambda value: value + 1)
        .step("double", lambda value: value * 2)
    )

    result = workflow.run(3)

    assert result.name == "numbers"
    assert result.output == 8
    assert result.steps == ["add-one", "double"]


def test_workflow_reflect_pauses_with_prompt_metadata() -> None:
    workflow = (
        Workflow("draft")
        .step("clean", lambda value: value.strip())
        .reflect("Check if the output matches the user's goal", name="goal-check")
        .step("finish", lambda value: f"Done: {value}")
    )

    result = workflow.run("  Pyxis  ")

    assert result.paused is True
    assert result.output == "Pyxis"
    assert result.steps == ["clean"]
    assert result.metadata == {
        "kind": "reflect",
        "reason": "Workflow paused for reflection.",
        "step": "goal-check",
        "prompt": "Check if the output matches the user's goal",
    }


def test_workflow_ask_and_revise_steps_pause_for_user_calibration() -> None:
    ask_result = Workflow("plan").ask("Does this direction look right?").run("draft")
    revise_result = Workflow("plan").revise("What should change?").run("draft")

    assert ask_result.paused is True
    assert ask_result.metadata["kind"] == "ask"
    assert ask_result.metadata["prompt"] == "Does this direction look right?"
    assert revise_result.paused is True
    assert revise_result.metadata["kind"] == "revise"
    assert revise_result.metadata["prompt"] == "What should change?"


def test_session_workflow_pauses_at_checkpoint() -> None:
    workflow = (
        Workflow("numbers")
        .step("add-one", lambda value: value + 1)
        .checkpoint("Review the intermediate value.", name="review")
        .step("double", lambda value: value * 2)
    )
    session = Pyxis(agent=Agent(name="navigator")).session()

    result = session.run(workflow, 3)

    assert result.paused is True
    assert result.output == 4
    assert result.steps == ["add-one"]
    assert result.checkpoint is not None
    assert result.checkpoint.status == CheckpointStatus.PENDING
    assert result.checkpoint.payload["workflow"] == "numbers"


def test_session_workflow_reflect_creates_user_facing_checkpoint() -> None:
    workflow = (
        Workflow("draft")
        .step("clean", lambda value: value.strip())
        .reflect("Check if the output matches the user's goal", name="goal-check")
        .step("finish", lambda value: f"Done: {value}")
    )
    session = Pyxis(agent=Agent(name="navigator")).session()

    result = session.run(workflow, "  Pyxis  ")

    assert result.paused is True
    assert result.checkpoint is not None
    assert result.checkpoint.action == "workflow_reflect"
    assert result.checkpoint.summary == "Workflow 'draft' wants to reflect before continuing."
    assert result.checkpoint.risk_reason == "Workflow paused for reflection."
    assert result.checkpoint.preview == "Check if the output matches the user's goal"
    assert result.checkpoint.payload["step_kind"] == "reflect"
    assert result.checkpoint.payload["prompt"] == "Check if the output matches the user's goal"


def test_session_resumes_reflective_workflow_after_approval() -> None:
    workflow = (
        Workflow("draft")
        .step("clean", lambda value: value.strip())
        .ask("Does this direction look right?")
        .step("finish", lambda value: f"Done: {value}")
    )
    session = Pyxis(agent=Agent(name="navigator")).session()
    paused = session.run(workflow, "  Pyxis  ")
    assert paused.checkpoint is not None

    session.approve_checkpoint(paused.checkpoint.id)
    resumed = session.resume_workflow(paused.checkpoint.id)

    assert resumed.paused is False
    assert resumed.output == "Done: Pyxis"
    assert resumed.steps == ["clean", "finish"]


def test_session_resumes_approved_workflow_checkpoint() -> None:
    workflow = (
        Workflow("numbers")
        .step("add-one", lambda value: value + 1)
        .checkpoint("Review the intermediate value.", name="review")
        .step("double", lambda value: value * 2)
    )
    session = Pyxis(agent=Agent(name="navigator")).session()
    paused = session.run(workflow, 3)
    assert paused.checkpoint is not None

    session.approve_checkpoint(paused.checkpoint.id)
    resumed = session.resume_workflow(paused.checkpoint.id)

    assert resumed.paused is False
    assert resumed.output == 8
    assert resumed.steps == ["add-one", "double"]
    assert paused.checkpoint.id not in session.pending_workflows


def test_pending_workflow_checkpoint_cannot_resume_before_approval() -> None:
    workflow = Workflow("numbers").checkpoint("Review.")
    session = Pyxis(agent=Agent(name="navigator")).session()
    paused = session.run(workflow, 3)
    assert paused.checkpoint is not None

    with pytest.raises(CheckpointNotApproved):
        session.resume_workflow(paused.checkpoint.id)


def test_rejected_workflow_checkpoint_cannot_resume() -> None:
    workflow = Workflow("numbers").checkpoint("Review.")
    session = Pyxis(agent=Agent(name="navigator")).session()
    paused = session.run(workflow, 3)
    assert paused.checkpoint is not None

    session.reject_checkpoint(paused.checkpoint.id)

    with pytest.raises(CheckpointRejected):
        session.resume_workflow(paused.checkpoint.id)


def test_workflow_events_include_pause_and_resume() -> None:
    workflow = Workflow("numbers").checkpoint("Review.").step("double", lambda value: value * 2)
    session = Pyxis(agent=Agent(name="navigator")).session()
    paused = session.run(workflow, 3)
    assert paused.checkpoint is not None

    session.approve_checkpoint(paused.checkpoint.id)
    session.resume_workflow(paused.checkpoint.id)

    event_types = [event.type for event in session.events]
    assert "WorkflowStarted" in event_types
    assert "WorkflowPaused" in event_types
    assert "WorkflowResumed" in event_types
    assert "WorkflowCompleted" in event_types
