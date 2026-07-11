from pathlib import Path

import os
import subprocess

import pytest

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


def test_run_tests_ignores_stale_bytecode_after_same_size_rewrite(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("PYTHONPYCACHEPREFIX", raising=False)
    monkeypatch.delenv("PYTHONDONTWRITEBYTECODE", raising=False)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "value.py"
    source.write_text("def value():\n    return 1\n", encoding="utf-8")
    (workspace / "test_value.py").write_text(
        "from value import value\n\n\ndef test_value():\n    assert value() == 2\n",
        encoding="utf-8",
    )
    fixed_timestamp = 1_700_000_000
    os.utime(source, (fixed_timestamp, fixed_timestamp))
    policy = load_policy("strict_demo", Path("config/policies"))
    dispatcher = build_default_dispatcher(
        GuardrailEngine(policy, workspace), workspace, policy
    )

    first = dispatcher.dispatch(_run_tests_action())
    assert first.status == "failed"

    source.write_text("def value():\n    return 2\n", encoding="utf-8")
    os.utime(source, (fixed_timestamp, fixed_timestamp))

    second = dispatcher.dispatch(_run_tests_action())

    assert second.status == "ok"
    assert second.feedback[0].type is FeedbackType.TEST_PASSED


def test_sample_workspace_starts_with_failing_test() -> None:
    workspace = Path("demos/sample_workspace")
    assert (workspace / "calculator.py").exists()
    assert (workspace / "test_calculator.py").exists()


def _run_tests_action() -> Action:
    return Action(
        kind=ActionKind.TOOL,
        tool="run_tests",
        args={"target": "."},
        reason="run tests",
        expectation="structured result",
    )


def test_command_timeout_is_structured_timeout_result(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    policy = load_policy("strict_demo", Path("config/policies"))
    dispatcher = build_default_dispatcher(GuardrailEngine(policy, workspace), workspace, policy)

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["python", "-m", "pytest"], timeout=1)

    monkeypatch.setattr(subprocess, "run", timeout)
    result = dispatcher.dispatch(_run_tests_action())

    assert result.status == "timeout"
    assert result.feedback[0].type is FeedbackType.TIMEOUT


@pytest.mark.parametrize(
    "error",
    [
        FileNotFoundError("raw missing executable path"),
        UnicodeDecodeError("utf-8", b"bad", 0, 1, "raw decode detail"),
        OSError("raw filesystem detail"),
    ],
)
def test_command_runtime_errors_are_structured_failed_results(
    tmp_path: Path, monkeypatch, error: Exception
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    policy = load_policy("strict_demo", Path("config/policies"))
    dispatcher = build_default_dispatcher(GuardrailEngine(policy, workspace), workspace, policy)

    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(subprocess, "run", fail)
    result = dispatcher.dispatch(_run_tests_action())

    assert result.status == "failed"
    assert "raw " not in result.model_dump_json()
