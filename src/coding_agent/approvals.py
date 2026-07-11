from __future__ import annotations

import uuid

from coding_agent.domain import (
    Action,
    ApprovalRequest,
    ApprovalState,
    FeedbackSignal,
    ToolResult,
)
from coding_agent.store import SqliteStore


class ApprovalService:
    def __init__(self, store: SqliteStore) -> None:
        self.store = store

    def create(
        self,
        run_id: str,
        action: Action,
        rules: list[str],
        reason: str,
        step_index: int,
        feedback: list[FeedbackSignal],
    ) -> ApprovalRequest:
        if not action.id:
            action = action.model_copy(update={"id": f"action-{uuid.uuid4().hex[:12]}"})
        request = ApprovalRequest(
            id=f"approval-{uuid.uuid4().hex[:12]}",
            run_id=run_id,
            action_id=action.id,
            action=action,
            state=ApprovalState.PENDING,
            rules=rules,
            reason=reason,
            step_index=step_index,
            feedback=feedback,
        )
        self.store.create_approval(request)
        return request

    def approve_once(self, request_id: str, reviewer: str, reason: str) -> ApprovalRequest:
        return self._transition(request_id, ApprovalState.APPROVED_ONCE, reviewer, reason)

    def reject(self, request_id: str, reviewer: str, reason: str) -> ApprovalRequest:
        return self._transition(request_id, ApprovalState.REJECTED, reviewer, reason)

    def request_revision(self, request_id: str, reviewer: str, reason: str) -> ApprovalRequest:
        return self._transition(request_id, ApprovalState.REVISION_REQUESTED, reviewer, reason)

    def cancel(self, request_id: str, reviewer: str, reason: str) -> ApprovalRequest:
        return self._transition(request_id, ApprovalState.CANCELLED, reviewer, reason)

    def get(self, request_id: str) -> ApprovalRequest:
        return self.store.get_approval(request_id)

    def list_pending(self) -> list[ApprovalRequest]:
        return self.store.list_approvals(ApprovalState.PENDING)

    def list(self, state: ApprovalState | None = None) -> list[ApprovalRequest]:
        return self.store.list_approvals(state)

    def record_execution(self, request_id: str, result: ToolResult) -> ApprovalRequest:
        return self.store.record_approval_execution(request_id, result)

    def _transition(
        self,
        request_id: str,
        state: ApprovalState,
        reviewer: str,
        reason: str,
    ) -> ApprovalRequest:
        return self.store.transition_approval(request_id, state, reviewer, reason)
