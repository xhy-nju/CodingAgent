from pathlib import Path

import pytest

from coding_agent.agent_loop import AgentLoop
from coding_agent.approvals import ApprovalService
from coding_agent.domain import ApprovalState, ToolResult
from coding_agent.events import EventBus
from coding_agent.guardrails import GuardrailEngine
from coding_agent.llm import LLMContext, LLMProvider, MockLLMProvider
from coding_agent.memory import MemoryService
from coding_agent.policies import load_policy
from coding_agent.store import SqliteStore
from coding_agent.tools.base import ToolSpec
from coding_agent.tools.dispatcher import build_default_dispatcher


class ApprovalThenFinalProvider(LLMProvider):
    def next_action(self, context: LLMContext) -> str:
        if context.step_index == 0:
            return (
                '{"kind":"tool","tool":"run_command","args":{"command":["pytest"]},'
                '"reason":"run approved command","expectation":"command result"}'
            )
        return '{"kind":"final","args":{},"reason":"done","expectation":"stop"}'


class CapturingFinalProvider(LLMProvider):
    def __init__(self) -> None:
        self.contexts: list[LLMContext] = []

    def next_action(self, context: LLMContext) -> str:
        self.contexts.append(context)
        return '{"kind":"final","args":{},"reason":"done","expectation":"stop"}'


class RememberThenFinalProvider(LLMProvider):
    def next_action(self, context: LLMContext) -> str:
        if context.step_index == 0:
            return (
                '{"kind":"remember","args":{"content":"Prefer focused tests",'
                '"tags":["pytest"],"scope":"project"},"reason":"save lesson",'
                '"expectation":"memory persisted"}'
            )
        return '{"kind":"final","args":{},"reason":"done","expectation":"stop"}'


class ListThenFinalProvider(LLMProvider):
    def __init__(self) -> None:
        self.contexts: list[LLMContext] = []

    def next_action(self, context: LLMContext) -> str:
        self.contexts.append(context)
        if context.step_index == 0:
            return (
                '{"kind":"tool","tool":"list_files","args":{},'
                '"reason":"inspect workspace","expectation":"file list"}'
            )
        return '{"kind":"final","args":{},"reason":"done","expectation":"stop"}'


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


def test_loop_can_start_then_continue_a_persisted_run(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    loop = _loop(tmp_path, workspace, "dangerous_action")

    run_id = loop.start_run("demonstrate guardrail")
    assert loop.store.get_run(run_id)["status"] == "running"

    summary = loop.continue_run(run_id)

    assert summary.run_id == run_id
    assert summary.status == "failed"


def test_fail_run_records_terminal_feedback(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    loop = _loop(tmp_path, workspace, "dangerous_action")
    run_id = loop.start_run("provider failure")

    summary = loop.fail_run(run_id, "provider request failed")

    assert summary.status == "failed"
    assert summary.feedback[0].summary == "provider request failed"
    assert loop.store.get_run(run_id)["finished_at"] is not None


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


def test_successful_tool_observation_is_injected_into_next_model_step(tmp_path: Path) -> None:
    workspace = tmp_path / "observation-workspace"
    workspace.mkdir()
    (workspace / "calculator.py").write_text("def add(a, b): return a - b\n", encoding="utf-8")
    store = SqliteStore(tmp_path / "observation.db")
    policy = load_policy("strict_demo", Path("config/policies"))
    memory = MemoryService(store)
    provider = ListThenFinalProvider()
    loop = AgentLoop(
        store=store,
        events=EventBus(store),
        memory=memory,
        dispatcher=build_default_dispatcher(
            GuardrailEngine(policy, workspace), workspace, policy, memory=memory
        ),
        llm=provider,
        workspace=workspace,
        policy_profile="strict_demo",
        llm_mode="real",
        max_steps=3,
    )

    summary = loop.run("inspect calculator")

    assert summary.status == "succeeded"
    assert provider.contexts[1].feedback[0].type.value == "tool_observation"
    assert provider.contexts[1].feedback[0].details["artifacts"]["files"] == [
        "calculator.py"
    ]


def _approval_loop(tmp_path: Path) -> tuple[AgentLoop, SqliteStore, list[str]]:
    workspace = tmp_path / "approval-workspace"
    workspace.mkdir()
    store = SqliteStore(tmp_path / "approval.db")
    policy = load_policy("strict_demo", Path("config/policies"))
    memory = MemoryService(store)
    dispatcher = build_default_dispatcher(
        GuardrailEngine(policy, workspace), workspace, policy, memory=memory
    )
    calls: list[str] = []

    def approved_command(args, context) -> ToolResult:
        calls.append("executed")
        return ToolResult(status="ok", stdout_summary="approved command ran")

    dispatcher.register(
        ToolSpec(name="run_command", description="count approved execution", handler=approved_command)
    )
    return (
        AgentLoop(
            store=store,
            events=EventBus(store),
            memory=memory,
            dispatcher=dispatcher,
            llm=ApprovalThenFinalProvider(),
            workspace=workspace,
            policy_profile="strict_demo",
            llm_mode="mock",
            max_steps=3,
        ),
        store,
        calls,
    )


def test_approved_action_executes_exactly_once_then_run_resumes(tmp_path: Path) -> None:
    loop, store, calls = _approval_loop(tmp_path)

    waiting = loop.run("approval workflow")
    approval = ApprovalService(store).list_pending()[0]

    assert waiting.status == "waiting_approval"
    assert waiting.pending_approval_id == approval.id
    assert store.get_run(waiting.run_id)["status"] == "waiting_approval"
    assert calls == []

    resumed = loop.resolve_approval(
        approval.id, decision="approve", reviewer="admin", reason="command reviewed"
    )

    assert resumed.status == "succeeded"
    assert calls == ["executed"]
    assert ApprovalService(store).get(approval.id).state is ApprovalState.APPROVED_ONCE
    with pytest.raises(ValueError, match="pending"):
        loop.resolve_approval(
            approval.id, decision="approve", reviewer="admin", reason="duplicate"
        )
    assert calls == ["executed"]


def test_rejected_action_never_executes_and_rejection_is_feedback(tmp_path: Path) -> None:
    loop, store, calls = _approval_loop(tmp_path)
    waiting = loop.run("approval workflow")
    approval = ApprovalService(store).list_pending()[0]

    resumed = loop.resolve_approval(
        approval.id, decision="reject", reviewer="admin", reason="risk not accepted"
    )

    assert waiting.status == "waiting_approval"
    assert resumed.status == "succeeded"
    assert calls == []
    assert any(item.type == "approval_rejected" for item in resumed.feedback)
    assert ApprovalService(store).get(approval.id).state is ApprovalState.REJECTED


def test_scoped_memory_is_injected_before_provider_call(tmp_path: Path) -> None:
    workspace = tmp_path / "memory-workspace"
    workspace.mkdir()
    store = SqliteStore(tmp_path / "memory-agent.db")
    policy = load_policy("strict_demo", Path("config/policies"))
    memory = MemoryService(store)
    memory.write_summary(
        scope="project",
        tags=["preference"],
        content="Run the narrow pytest target first",
        source_run_id=None,
    )
    memory.write_summary(
        scope="other-project",
        tags=["preference"],
        content="This belongs to a different scope",
        source_run_id=None,
    )
    provider = CapturingFinalProvider()
    loop = AgentLoop(
        store=store,
        events=EventBus(store),
        memory=memory,
        dispatcher=build_default_dispatcher(
            GuardrailEngine(policy, workspace), workspace, policy, memory=memory
        ),
        llm=provider,
        workspace=workspace,
        policy_profile="strict_demo",
        llm_mode="mock",
        max_steps=2,
    )

    loop.run("fix focused tests")

    assert [record.content for record in provider.contexts[0].memories] == [
        "Run the narrow pytest target first"
    ]


def test_remember_action_writes_policy_scoped_memory_and_continues(tmp_path: Path) -> None:
    workspace = tmp_path / "remember-workspace"
    workspace.mkdir()
    store = SqliteStore(tmp_path / "remember-agent.db")
    policy = load_policy("strict_demo", Path("config/policies"))
    memory = MemoryService(store)
    loop = AgentLoop(
        store=store,
        events=EventBus(store),
        memory=memory,
        dispatcher=build_default_dispatcher(
            GuardrailEngine(policy, workspace), workspace, policy, memory=memory
        ),
        llm=RememberThenFinalProvider(),
        workspace=workspace,
        policy_profile="strict_demo",
        llm_mode="mock",
        max_steps=2,
    )

    summary = loop.run("remember a lesson")

    assert summary.status == "succeeded"
    assert [record.content for record in memory.search([], "", scope="project")] == [
        "Prefer focused tests"
    ]
    assert "memory.written" in [
        event["event_type"] for event in store.list_events(summary.run_id)
    ]
