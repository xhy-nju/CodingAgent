from pathlib import Path

import pytest

from coding_agent.approvals import ApprovalService
from coding_agent.domain import Action, ActionKind, ApprovalState
from coding_agent.store import SqliteStore


def test_approval_lifecycle_is_persisted_with_original_action(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "agent.db")
    run_id = store.create_run(
        task="run approved tests",
        workspace=str(tmp_path),
        policy_profile="strict_demo",
        llm_mode="mock",
    )
    service = ApprovalService(store)
    action = Action(
        id="action-1",
        kind=ActionKind.TOOL,
        tool="run_command",
        args={"command": ["pytest"]},
        reason="manual command",
        expectation="approval",
    )

    request = service.create(
        run_id=run_id,
        action=action,
        rules=["tool.requires_approval"],
        reason="strict demo",
        step_index=2,
        feedback=[],
    )
    persisted = ApprovalService(SqliteStore(tmp_path / "agent.db")).get(request.id)
    approved = service.approve_once(request.id, reviewer="admin", reason="safe pytest command")

    assert persisted.action == action
    assert persisted.run_id == run_id
    assert persisted.step_index == 2
    assert approved.state is ApprovalState.APPROVED_ONCE
    assert approved.reviewer == "admin"
    assert approved.reviewer_reason == "safe pytest command"


def test_approval_can_only_leave_pending_once(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "agent.db")
    run_id = store.create_run("task", str(tmp_path), "strict_demo", "mock")
    service = ApprovalService(store)
    request = service.create(
        run_id=run_id,
        action=Action(
            id="action-1",
            kind=ActionKind.TOOL,
            tool="run_command",
            args={"command": ["pytest"]},
            reason="manual command",
            expectation="approval",
        ),
        rules=["tool.requires_approval"],
        reason="strict demo",
        step_index=0,
        feedback=[],
    )

    service.reject(request.id, reviewer="admin", reason="not needed")

    with pytest.raises(ValueError, match="pending"):
        service.approve_once(request.id, reviewer="admin", reason="changed mind")
