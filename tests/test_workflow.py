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
