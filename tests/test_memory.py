from pathlib import Path

from coding_agent.domain import Action, ActionKind
from coding_agent.guardrails import GuardrailEngine
from coding_agent.memory import MemoryService
from coding_agent.policies import load_policy
from coding_agent.store import SqliteStore
from coding_agent.tools.dispatcher import build_default_dispatcher


def test_memory_search_is_tag_and_keyword_based(tmp_path: Path) -> None:
    service = MemoryService(SqliteStore(tmp_path / "agent.db"))
    service.write_summary(
        scope="project",
        tags=["feedback", "pytest"],
        content="When pytest reports assert 5 == 4, inspect calculator.add",
        source_run_id="run-1",
    )

    records = service.search(tags=["feedback"], query="calculator")

    assert len(records) == 1
    assert records[0].content.startswith("When pytest reports")


def test_sensitive_memory_is_not_returned(tmp_path: Path) -> None:
    service = MemoryService(SqliteStore(tmp_path / "agent.db"))
    service.write_summary(
        scope="project",
        tags=["credential"],
        content="provider token demo-redaction-value-123456",
        source_run_id=None,
        sensitive=True,
    )

    records = service.search(tags=["credential"], query="api")

    assert records == []


def test_memory_tools_write_and_search_through_dispatcher(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    policy = load_policy("strict_demo", Path("config/policies"))
    memory = MemoryService(SqliteStore(tmp_path / "agent.db"))
    dispatcher = build_default_dispatcher(
        GuardrailEngine(policy, workspace),
        workspace,
        policy,
        memory=memory,
    )

    write_result = dispatcher.dispatch(
        Action(
            kind=ActionKind.TOOL,
            tool="memory_write",
            args={
                "scope": "project",
                "tags": ["feedback"],
                "content": "Prefer running pytest before claiming the task is fixed",
                "source_run_id": "run-1",
            },
            reason="remember feedback",
            expectation="memory id is returned",
        )
    )
    search_result = dispatcher.dispatch(
        Action(
            kind=ActionKind.TOOL,
            tool="memory_search",
            args={"tags": ["feedback"], "query": "pytest"},
            reason="retrieve feedback",
            expectation="memory record is returned",
        )
    )

    assert write_result.status == "ok"
    assert write_result.artifacts["memory_id"].startswith("mem-")
    assert search_result.status == "ok"
    assert search_result.artifacts["records"][0]["content"].startswith("Prefer running pytest")
