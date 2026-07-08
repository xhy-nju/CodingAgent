from __future__ import annotations

from pathlib import Path

from coding_agent.domain import (
    Action,
    FeedbackSignal,
    FeedbackType,
    GuardrailDecisionType,
    ToolResult,
)
from coding_agent.guardrails import GuardrailEngine
from coding_agent.policies import PolicyProfile
from coding_agent.tools.base import ToolContext, ToolSpec
from coding_agent.tools.commands import run_command, run_tests
from coding_agent.tools.files import list_files, read_file, write_file


class ToolDispatcher:
    def __init__(self, guardrails: GuardrailEngine, context: ToolContext) -> None:
        self.guardrails = guardrails
        self.context = context
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def dispatch(self, action: Action) -> ToolResult:
        decision = self.guardrails.evaluate(action)
        if decision.decision is GuardrailDecisionType.DENY:
            return ToolResult(
                status="blocked",
                stderr_summary=decision.message,
                feedback=[
                    FeedbackSignal(
                        type=FeedbackType.GUARDRAIL_BLOCKED,
                        severity="error",
                        summary=decision.message,
                        details={"rules": decision.rules},
                    )
                ],
            )
        if decision.decision is GuardrailDecisionType.NEEDS_APPROVAL:
            return ToolResult(
                status="needs_approval",
                stderr_summary=decision.message,
                artifacts={"rules": decision.rules},
            )
        if not action.tool or action.tool not in self._tools:
            return ToolResult(status="failed", stderr_summary=f"unknown tool: {action.tool}")
        return self._tools[action.tool].handler(action.args, self.context)


def memory_search(args: dict[str, object], context: ToolContext) -> ToolResult:
    if context.memory is None:
        return ToolResult(status="failed", stderr_summary="memory service not configured")
    tags = [str(tag) for tag in args.get("tags", [])]
    query = str(args.get("query", ""))
    records = [record.model_dump() for record in context.memory.search(tags=tags, query=query)]
    return ToolResult(status="ok", artifacts={"records": records})


def memory_write(args: dict[str, object], context: ToolContext) -> ToolResult:
    if context.memory is None:
        return ToolResult(status="failed", stderr_summary="memory service not configured")
    memory_id = context.memory.write_summary(
        scope=str(args.get("scope", "project")),
        tags=[str(tag) for tag in args.get("tags", [])],
        content=str(args["content"]),
        source_run_id=str(args["source_run_id"]) if args.get("source_run_id") else None,
        sensitive=bool(args.get("sensitive", False)),
    )
    return ToolResult(status="ok", artifacts={"memory_id": memory_id})


def build_default_dispatcher(
    guardrails: GuardrailEngine,
    workspace: Path,
    policy: PolicyProfile,
    memory: object | None = None,
) -> ToolDispatcher:
    dispatcher = ToolDispatcher(guardrails, ToolContext(workspace=workspace, policy=policy, memory=memory))
    dispatcher.register(ToolSpec(name="list_files", description="List workspace files", handler=list_files))
    dispatcher.register(ToolSpec(name="read_file", description="Read a workspace text file", handler=read_file))
    dispatcher.register(ToolSpec(name="write_file", description="Write a workspace text file", handler=write_file))
    dispatcher.register(ToolSpec(name="run_tests", description="Run pytest in workspace", handler=run_tests))
    dispatcher.register(ToolSpec(name="run_command", description="Run a guarded command", handler=run_command))
    dispatcher.register(ToolSpec(name="memory_search", description="Search deterministic memory", handler=memory_search))
    dispatcher.register(ToolSpec(name="memory_write", description="Write deterministic memory", handler=memory_write))
    return dispatcher
