from pathlib import Path

from coding_agent.domain import Action, ActionKind, GuardrailDecisionType
from coding_agent.guardrails import GuardrailEngine
from coding_agent.policies import load_policy
from coding_agent.redaction import redact_secrets


def test_denies_path_outside_workspace(tmp_path: Path) -> None:
    policy = load_policy("strict_demo", Path("config/policies"))
    engine = GuardrailEngine(policy=policy, workspace=tmp_path)
    action = Action(
        kind=ActionKind.TOOL,
        tool="read_file",
        args={"path": "../outside.txt"},
        reason="read outside",
        expectation="should be blocked",
    )

    decision = engine.evaluate(action)

    assert decision.decision is GuardrailDecisionType.DENY
    assert "path.outside_workspace" in decision.rules


def test_run_command_requires_approval_in_strict_demo(tmp_path: Path) -> None:
    policy = load_policy("strict_demo", Path("config/policies"))
    engine = GuardrailEngine(policy=policy, workspace=tmp_path)
    action = Action(
        kind=ActionKind.TOOL,
        tool="run_command",
        args={"command": ["pytest"]},
        reason="manual shell",
        expectation="approval required",
    )

    decision = engine.evaluate(action)

    assert decision.decision is GuardrailDecisionType.NEEDS_APPROVAL
    assert "tool.requires_approval" in decision.rules


def test_denies_recursive_delete_fragment(tmp_path: Path) -> None:
    policy = load_policy("balanced_dev", Path("config/policies"))
    engine = GuardrailEngine(policy=policy, workspace=tmp_path)
    action = Action(
        kind=ActionKind.TOOL,
        tool="run_command",
        args={"command": ["blocked-delete", "--recursive", "."]},
        reason="blocked cleanup",
        expectation="blocked",
    )

    decision = engine.evaluate(action)

    assert decision.decision is GuardrailDecisionType.DENY
    assert "command.denied_fragment" in decision.rules


def test_denies_dangerous_command_when_model_returns_string(tmp_path: Path) -> None:
    policy = load_policy("strict_demo", Path("config/policies"))
    engine = GuardrailEngine(policy=policy, workspace=tmp_path)
    action = Action(
        kind=ActionKind.TOOL,
        tool="run_command",
        args={"command": "rm -rf ."},
        reason="unsafe string command",
        expectation="blocked",
    )

    decision = engine.evaluate(action)

    assert decision.decision is GuardrailDecisionType.DENY
    assert "command.denied_fragment" in decision.rules


def test_string_command_is_normalized_before_prefix_check(tmp_path: Path) -> None:
    policy = load_policy("strict_demo", Path("config/policies"))
    engine = GuardrailEngine(policy=policy, workspace=tmp_path)
    action = Action(
        kind=ActionKind.TOOL,
        tool="run_command",
        args={"command": "pytest -q"},
        reason="run tests",
        expectation="approval required",
    )

    decision = engine.evaluate(action)

    assert decision.decision is GuardrailDecisionType.NEEDS_APPROVAL
    assert "tool.requires_approval" in decision.rules


def test_redacts_provider_token_like_values() -> None:
    redacted, labels = redact_secrets("token=demo-redaction-value-123456")

    assert "demo-redaction-value-123456" not in redacted
    assert labels == ["provider_token"]
