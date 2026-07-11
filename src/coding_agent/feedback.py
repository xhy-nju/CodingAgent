from __future__ import annotations

import re

from coding_agent.domain import FeedbackSignal, FeedbackType, ToolResult

COUNT_RE = re.compile(r"(?P<count>\d+)\s+(?P<kind>failed|passed|error|errors)")


def _counts(text: str) -> dict[str, int]:
    result = {"failed": 0, "passed": 0, "errors": 0}
    for match in COUNT_RE.finditer(text):
        count = int(match.group("count"))
        kind = match.group("kind")
        if kind == "error":
            kind = "errors"
        result[kind] = result.get(kind, 0) + count
    return result


def parse_pytest_output(exit_code: int, stdout: str, stderr: str) -> FeedbackSignal:
    combined = f"{stdout}\n{stderr}"
    counts = _counts(combined)
    if exit_code == 0:
        return FeedbackSignal(
            type=FeedbackType.TEST_PASSED,
            severity="info",
            summary=f"pytest passed: {counts['passed']} passed",
            details=counts,
        )
    return FeedbackSignal(
        type=FeedbackType.TEST_FAILED,
        severity="error",
        summary=f"pytest failed: {counts['failed']} failed, {counts['passed']} passed",
        details=counts | {"exit_code": exit_code},
    )


def feedback_from_tool_result(result: ToolResult) -> list[FeedbackSignal]:
    if result.feedback:
        return result.feedback
    if result.status == "blocked":
        return [
            FeedbackSignal(
                type=FeedbackType.GUARDRAIL_BLOCKED,
                severity="error",
                summary=result.stderr_summary or "guardrail blocked action",
            )
        ]
    if result.status == "failed":
        return [
            FeedbackSignal(
                type=FeedbackType.COMMAND_FAILED,
                severity="error",
                summary=result.stderr_summary or "tool failed",
            )
        ]
    return []
