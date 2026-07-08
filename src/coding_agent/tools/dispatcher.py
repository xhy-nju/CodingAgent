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


def build_default_dispatcher(
    guardrails: GuardrailEngine,
    workspace: Path,
    policy: PolicyProfile,
) -> ToolDispatcher:
    dispatcher = ToolDispatcher(guardrails, ToolContext(workspace=workspace, policy=policy))
    dispatcher.register(ToolSpec(name="list_files", description="List workspace files", handler=list_files))
    dispatcher.register(ToolSpec(name="read_file", description="Read a workspace text file", handler=read_file))
    dispatcher.register(ToolSpec(name="write_file", description="Write a workspace text file", handler=write_file))
    return dispatcher
