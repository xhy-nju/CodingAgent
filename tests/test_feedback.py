from coding_agent.domain import FeedbackType, ToolResult
from coding_agent.feedback import feedback_from_tool_result, parse_pytest_output


def test_parse_pytest_failure_summary() -> None:
    stdout = """
    ============================= test session starts =============================
    FAILED test_calculator.py::test_add - assert 5 == 4
    =========================== 1 failed, 2 passed in 0.05s =======================
    """

    feedback = parse_pytest_output(exit_code=1, stdout=stdout, stderr="")

    assert feedback.type is FeedbackType.TEST_FAILED
    assert feedback.severity == "error"
    assert feedback.details["failed"] == 1
    assert feedback.details["passed"] == 2


def test_parse_pytest_pass_summary() -> None:
    feedback = parse_pytest_output(
        exit_code=0,
        stdout="=========================== 3 passed in 0.03s ===========================",
        stderr="",
    )

    assert feedback.type is FeedbackType.TEST_PASSED
    assert feedback.details["passed"] == 3


def test_feedback_from_blocked_tool_result() -> None:
    result = ToolResult(status="blocked", stderr_summary="Action violates guardrail policy")

    feedback = feedback_from_tool_result(result)

    assert feedback[0].type is FeedbackType.GUARDRAIL_BLOCKED


def test_successful_tool_result_becomes_model_observation() -> None:
    result = ToolResult(
        status="ok",
        stdout_summary="calculator.py\ntest_calculator.py",
        artifacts={"files": ["calculator.py", "test_calculator.py"]},
    )

    feedback = feedback_from_tool_result(result)

    assert feedback[0].type is FeedbackType.TOOL_OBSERVATION
    assert feedback[0].details["stdout"] == "calculator.py\ntest_calculator.py"
    assert feedback[0].details["artifacts"]["files"] == [
        "calculator.py",
        "test_calculator.py",
    ]
