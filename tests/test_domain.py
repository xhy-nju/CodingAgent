from coding_agent.domain import (
    Action,
    ActionKind,
    ApprovalRequest,
    ApprovalState,
    FeedbackSignal,
    FeedbackType,
    GuardrailDecision,
    GuardrailDecisionType,
    ToolResult,
)


def test_action_model_keeps_structured_arguments() -> None:
    action = Action(
        kind=ActionKind.TOOL,
        tool="read_file",
        args={"path": "sample/calculator.py"},
        reason="inspect implementation",
        expectation="read file text",
    )

    assert action.kind is ActionKind.TOOL
    assert action.tool == "read_file"
    assert action.args["path"] == "sample/calculator.py"


def test_guardrail_decision_records_rule_hits() -> None:
    decision = GuardrailDecision(
        decision=GuardrailDecisionType.DENY,
        rules=["path.outside_workspace"],
        message="Path is outside workspace",
    )

    assert decision.decision is GuardrailDecisionType.DENY
    assert decision.rules == ["path.outside_workspace"]


def test_feedback_and_tool_result_are_serializable() -> None:
    feedback = FeedbackSignal(
        type=FeedbackType.GUARDRAIL_BLOCKED,
        severity="error",
        summary="blocked unsafe action",
        details={"rule": "command.recursive_delete"},
    )
    result = ToolResult(
        status="blocked",
        stdout_summary="",
        stderr_summary="blocked unsafe action",
        feedback=[feedback],
    )

    dumped = result.model_dump()
    assert dumped["feedback"][0]["type"] == "guardrail_blocked"


def test_approval_request_starts_pending() -> None:
    action = Action(
        id="action-1",
        kind=ActionKind.TOOL,
        tool="run_command",
        args={"command": ["pytest"]},
        reason="run tests",
        expectation="test result",
    )
    approval = ApprovalRequest(
        id="approval-1",
        run_id="run-1",
        action_id="action-1",
        action=action,
        state=ApprovalState.PENDING,
        rules=["command.needs_human"],
        reason="command requires approval",
    )

    assert approval.state is ApprovalState.PENDING
