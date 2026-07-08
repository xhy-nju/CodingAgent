from __future__ import annotations

import uuid

from coding_agent.domain import Action, ApprovalRequest, ApprovalState


class ApprovalService:
    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}

    def create(self, action: Action, rules: list[str], reason: str) -> ApprovalRequest:
        if not action.id:
            action = action.model_copy(update={"id": f"action-{uuid.uuid4().hex[:12]}"})
        request = ApprovalRequest(
            id=f"approval-{uuid.uuid4().hex[:12]}",
            action_id=action.id,
            state=ApprovalState.PENDING,
            rules=rules,
            reason=reason,
        )
        self._requests[request.id] = request
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
        return self._requests[request_id]

    def _transition(
        self,
        request_id: str,
        state: ApprovalState,
        reviewer: str,
        reason: str,
    ) -> ApprovalRequest:
        current = self._requests[request_id]
        updated = current.model_copy(
            update={"state": state, "reviewer": reviewer, "reviewer_reason": reason}
        )
        self._requests[request_id] = updated
        return updated
