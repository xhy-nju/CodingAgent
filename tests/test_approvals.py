from coding_agent.approvals import ApprovalService
from coding_agent.domain import Action, ActionKind, ApprovalState


def test_approval_lifecycle_records_reviewer_reason() -> None:
    service = ApprovalService()
    action = Action(
        id="action-1",
        kind=ActionKind.TOOL,
        tool="run_command",
        args={"command": ["pytest"]},
        reason="manual command",
        expectation="approval",
    )

    request = service.create(action, rules=["tool.requires_approval"], reason="strict demo")
    approved = service.approve_once(request.id, reviewer="admin", reason="safe pytest command")

    assert approved.state is ApprovalState.APPROVED_ONCE
    assert approved.reviewer == "admin"
    assert approved.reviewer_reason == "safe pytest command"
