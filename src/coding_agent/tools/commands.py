from __future__ import annotations

import subprocess
import time

from coding_agent.domain import ToolResult
from coding_agent.feedback import parse_pytest_output
from coding_agent.tools.base import ToolContext


def run_tests(args: dict[str, object], context: ToolContext) -> ToolResult:
    target = str(args.get("target", "."))
    command = ["python", "-m", "pytest", target]
    start = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=context.workspace,
        text=True,
        capture_output=True,
        timeout=context.policy.tool_timeout_seconds,
        check=False,
    )
    duration_ms = int((time.monotonic() - start) * 1000)
    feedback = parse_pytest_output(completed.returncode, completed.stdout, completed.stderr)
    return ToolResult(
        status="ok" if completed.returncode == 0 else "failed",
        stdout_summary=completed.stdout[-4000:],
        stderr_summary=completed.stderr[-4000:],
        duration_ms=duration_ms,
        feedback=[feedback],
        artifacts={"command": command, "exit_code": completed.returncode},
    )


def run_command(args: dict[str, object], context: ToolContext) -> ToolResult:
    command = [str(part) for part in args["command"]]
    start = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=context.workspace,
        text=True,
        capture_output=True,
        timeout=context.policy.tool_timeout_seconds,
        check=False,
    )
    duration_ms = int((time.monotonic() - start) * 1000)
    return ToolResult(
        status="ok" if completed.returncode == 0 else "failed",
        stdout_summary=completed.stdout[-4000:],
        stderr_summary=completed.stderr[-4000:],
        duration_ms=duration_ms,
        artifacts={"command": command, "exit_code": completed.returncode},
    )
