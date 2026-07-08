from pathlib import Path

from coding_agent.agent_loop import AgentLoop
from coding_agent.events import EventBus
from coding_agent.guardrails import GuardrailEngine
from coding_agent.llm import MockLLMProvider
from coding_agent.memory import MemoryService
from coding_agent.policies import load_policy
from coding_agent.store import SqliteStore
from coding_agent.tools.dispatcher import build_default_dispatcher


def _loop(tmp_path: Path, workspace: Path, script_name: str) -> AgentLoop:
    store = SqliteStore(tmp_path / "agent.db")
    policy = load_policy("strict_demo", Path("config/policies"))
    memory = MemoryService(store)
    dispatcher = build_default_dispatcher(GuardrailEngine(policy, workspace), workspace, policy, memory=memory)
    return AgentLoop(
        store=store,
        events=EventBus(store),
        memory=memory,
        dispatcher=dispatcher,
        llm=MockLLMProvider(script_name=script_name),
        workspace=workspace,
        policy_profile="strict_demo",
        llm_mode="mock",
        max_steps=8,
    )


def test_mock_loop_blocks_dangerous_action(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    loop = _loop(tmp_path, workspace, "dangerous_action")

    summary = loop.run("demonstrate guardrail")

    assert summary.status == "failed"
    assert any(item.type == "guardrail_blocked" for item in summary.feedback)


def test_mock_loop_fixes_sample_after_feedback(tmp_path: Path) -> None:
    workspace = tmp_path / "sample"
    workspace.mkdir()
    (workspace / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (workspace / "test_calculator.py").write_text(
        "from calculator import add\n\n"
        "def test_add_positive_numbers():\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )
    loop = _loop(tmp_path, workspace, "bugfix_with_feedback")

    summary = loop.run("fix calculator")

    assert summary.status == "succeeded"
    assert "return a + b" in (workspace / "calculator.py").read_text(encoding="utf-8")
