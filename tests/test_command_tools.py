from pathlib import Path

from coding_agent.domain import Action, ActionKind, FeedbackType
from coding_agent.guardrails import GuardrailEngine
from coding_agent.policies import load_policy
from coding_agent.tools.dispatcher import build_default_dispatcher


def test_run_tests_produces_test_failed_feedback(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "test_sample.py").write_text("def test_fail():\n    assert 1 == 2\n", encoding="utf-8")
    policy = load_policy("strict_demo", Path("config/policies"))
    dispatcher = build_default_dispatcher(GuardrailEngine(policy, workspace), workspace, policy)

    result = dispatcher.dispatch(
        Action(
            kind=ActionKind.TOOL,
            tool="run_tests",
            args={"target": "."},
            reason="run tests",
            expectation="failure feedback",
        )
    )

    assert result.status == "failed"
    assert result.feedback[0].type is FeedbackType.TEST_FAILED


def test_sample_workspace_starts_with_failing_test() -> None:
    workspace = Path("demos/sample_workspace")
    assert (workspace / "calculator.py").exists()
    assert (workspace / "test_calculator.py").exists()
