from pathlib import Path

from coding_agent.domain import Action, ActionKind
from coding_agent.guardrails import GuardrailEngine
from coding_agent.policies import load_policy
from coding_agent.tools.dispatcher import build_default_dispatcher


def test_read_file_inside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "calculator.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8"
    )
    policy = load_policy("strict_demo", Path("config/policies"))
    dispatcher = build_default_dispatcher(GuardrailEngine(policy, workspace), workspace, policy)

    result = dispatcher.dispatch(
        Action(
            kind=ActionKind.TOOL,
            tool="read_file",
            args={"path": "calculator.py"},
            reason="read file",
            expectation="source text",
        )
    )

    assert result.status == "ok"
    assert "return a + b" in result.artifacts["content"]


def test_write_file_returns_diff_summary(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    policy = load_policy("strict_demo", Path("config/policies"))
    dispatcher = build_default_dispatcher(GuardrailEngine(policy, workspace), workspace, policy)

    result = dispatcher.dispatch(
        Action(
            kind=ActionKind.TOOL,
            tool="write_file",
            args={"path": "note.txt", "content": "hello\n"},
            reason="write file",
            expectation="file exists",
        )
    )

    assert result.status == "ok"
    assert (workspace / "note.txt").read_text(encoding="utf-8") == "hello\n"
    assert result.artifacts["diff_summary"] == "created note.txt"


def test_dispatcher_blocks_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    policy = load_policy("strict_demo", Path("config/policies"))
    dispatcher = build_default_dispatcher(GuardrailEngine(policy, workspace), workspace, policy)

    result = dispatcher.dispatch(
        Action(
            kind=ActionKind.TOOL,
            tool="read_file",
            args={"path": "../outside.txt"},
            reason="read outside",
            expectation="blocked",
        )
    )

    assert result.status == "blocked"
    assert result.feedback[0].type == "guardrail_blocked"
