from pyxis import ApprovalMode, ControlPolicy


def test_safe_default_policy_requires_high_risk_confirmation() -> None:
    decision = ControlPolicy.safe_default().decide(action="file_write", risk="high")

    assert decision.allowed is True
    assert decision.requires_confirmation is True
    assert decision.effective_risk == "high"


def test_policy_allow_auto_overrides_risk_confirmation() -> None:
    policy = ControlPolicy(
        require_confirmation_for_risk={"high"},
        allow_auto_for_actions={"summarize"},
    )

    decision = policy.decide(action="summarize", risk="high")

    assert decision.allowed is True
    assert decision.requires_confirmation is False


def test_policy_deny_overrides_allow_auto() -> None:
    policy = ControlPolicy(
        allow_auto_for_actions={"network_post"},
        deny_actions={"network_post"},
    )

    decision = policy.decide(action="network_post", risk="low")

    assert decision.allowed is False
    assert decision.requires_confirmation is False


def test_strict_policy_requires_confirmation_for_unlisted_action() -> None:
    policy = ControlPolicy(approval_mode=ApprovalMode.STRICT)

    decision = policy.decide(action="summarize", risk="low")

    assert decision.allowed is True
    assert decision.requires_confirmation is True
    assert decision.reason == "Strict approval mode requires confirmation."


def test_permissive_policy_only_uses_explicit_rules() -> None:
    policy = ControlPolicy.permissive()

    decision = policy.decide(action="file_write", risk="high")

    assert decision.allowed is True
    assert decision.requires_confirmation is False


def test_risk_override_changes_confirmation_decision() -> None:
    policy = ControlPolicy(
        require_confirmation_for_risk={"high"},
        risk_overrides={"network_post": "high"},
    )

    decision = policy.decide(action="network_post", risk="low")

    assert decision.risk == "low"
    assert decision.effective_risk == "high"
    assert decision.requires_confirmation is True
