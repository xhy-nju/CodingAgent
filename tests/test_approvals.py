import sqlite3
from pathlib import Path

import pytest
from keyring.errors import PasswordDeleteError

from coding_agent.approvals import ApprovalService
from coding_agent.credentials import CredentialService, CredentialSnapshot
from coding_agent.domain import (
    Action,
    ActionKind,
    ApprovalState,
    FeedbackSignal,
    FeedbackType,
    ToolResult,
)
from coding_agent.store import SqliteStore


class FakeKeyring:
    def __init__(self, token: str) -> None:
        self.token = token

    def get_password(self, service: str, username: str) -> str | None:
        return self.token

    def set_password(self, service: str, username: str, token: str) -> None:
        self.token = token

    def delete_password(self, service: str, username: str) -> None:
        if not self.token:
            raise PasswordDeleteError("credential not found")
        self.token = ""


def _assert_approval_and_run_rows_are_redacted(
    tmp_path: Path, token: str, snapshot: CredentialSnapshot
) -> None:
    store = SqliteStore(tmp_path / "agent.db", credential_snapshot=snapshot)
    run_id = store.create_run(
        task=f"task {token}",
        workspace=f"workspace {token}",
        policy_profile=f"profile {token}",
        llm_mode=f"mode {token}",
    )
    service = ApprovalService(store)
    feedback = FeedbackSignal(
        type=FeedbackType.TEST_FAILED,
        severity="error",
        summary=f"feedback {token}",
        details={"raw": token},
    )
    request = service.create(
        run_id=run_id,
        action=Action(
            id="action-1",
            kind=ActionKind.TOOL,
            tool="run_command",
            args={"raw": token},
            reason=f"action reason {token}",
            expectation=f"action expectation {token}",
        ),
        rules=[f"rule {token}"],
        reason=f"approval reason {token}",
        step_index=0,
        feedback=[feedback],
    )
    service.approve_once(
        request.id,
        reviewer=f"reviewer {token}",
        reason=f"review reason {token}",
    )
    service.record_execution(
        request.id,
        ToolResult(
            status="failed",
            stdout_summary=f"stdout {token}",
            stderr_summary=f"stderr {token}",
            artifacts={"raw": token},
            feedback=[feedback],
        ),
    )

    with sqlite3.connect(store.db_path) as conn:
        run_row = conn.execute(
            "select task, workspace, policy_profile, llm_mode from runs"
        ).fetchone()
        approval_row = conn.execute(
            "select action_json, rules_json, reason, feedback_json, reviewer, reviewer_reason, "
            "execution_result_json from approvals"
        ).fetchone()
    persisted = str(run_row) + str(approval_row)
    assert token not in persisted
    assert "provider_token:redacted" in persisted


def test_docker_secret_token_is_redacted_from_run_and_approval_rows(
    tmp_path: Path, monkeypatch
) -> None:
    token = "docker-secret-token-for-approval-test"
    secret = tmp_path / "openai_api_key"
    secret.write_text(f"{token}\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY_FILE", str(secret))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    _assert_approval_and_run_rows_are_redacted(tmp_path, token, CredentialService().resolve())


def test_injected_keyring_token_is_redacted_from_run_and_approval_rows(
    tmp_path: Path, monkeypatch
) -> None:
    token = "keyring-token-for-approval-test"
    monkeypatch.delenv("OPENAI_API_KEY_FILE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    snapshot = CredentialService(keyring_backend=FakeKeyring(token)).resolve()

    _assert_approval_and_run_rows_are_redacted(tmp_path, token, snapshot)


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
