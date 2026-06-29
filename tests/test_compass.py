from pyxis import Compass, CompassDecisionType


def test_compass_asks_for_empty_input() -> None:
    decision = Compass().decide("")

    assert decision.type == CompassDecisionType.ASK_CLARIFICATION


def test_compass_proposes_plan_for_workflow_request() -> None:
    decision = Compass().decide("帮我规划一个 workflow")

    assert decision.type == CompassDecisionType.PROPOSE_PLAN


def test_compass_requests_confirmation_when_required() -> None:
    decision = Compass().decide("send it", requires_confirmation=True)

    assert decision.type == CompassDecisionType.REQUEST_CONFIRMATION
