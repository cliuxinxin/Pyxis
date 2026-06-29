from pyxis import Workflow


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
