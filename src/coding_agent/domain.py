from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ActionKind(StrEnum):
    TOOL = "tool"
    REMEMBER = "remember"
    FINAL = "final"
    REQUEST_USER = "request_user"


class GuardrailDecisionType(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    NEEDS_APPROVAL = "needs_approval"
    REWRITE = "rewrite"


class FeedbackType(StrEnum):
    TEST_PASSED = "test_passed"
    TEST_FAILED = "test_failed"
    LINT_PASSED = "lint_passed"
    LINT_FAILED = "lint_failed"
    COMMAND_FAILED = "command_failed"
    GUARDRAIL_BLOCKED = "guardrail_blocked"
    APPROVAL_REJECTED = "approval_rejected"
    SCHEMA_ERROR = "schema_error"
    TIMEOUT = "timeout"
    FILE_DIFF = "file_diff"
    MEMORY_WRITTEN = "memory_written"


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalState(StrEnum):
    PENDING = "pending"
    APPROVED_ONCE = "approved_once"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    kind: ActionKind
    tool: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    reason: str
    expectation: str

    @model_validator(mode="after")
    def validate_kind_payload(self) -> "Action":
        if self.kind is ActionKind.TOOL:
            if not self.tool or not self.tool.strip():
                raise ValueError("tool actions require a non-empty tool name")
            return self

        if self.tool is not None:
            raise ValueError(f"{self.kind.value} actions forbid tool")
        if self.kind is ActionKind.FINAL:
            if self.args:
                raise ValueError("final actions require empty args")
            return self
        if self.kind is ActionKind.REMEMBER:
            allowed = {"scope", "tags", "content", "sensitive", "confidence"}
            if set(self.args) - allowed:
                raise ValueError("remember action has unsupported args")
            content = self.args.get("content")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("remember actions require non-empty content")
            tags = self.args.get("tags", [])
            if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
                raise ValueError("remember action tags must be a string list")
            scope = self.args.get("scope", "project")
            if not isinstance(scope, str) or not scope.strip():
                raise ValueError("remember action scope must be a non-empty string")
            return self
        if self.kind is ActionKind.REQUEST_USER:
            allowed = {"question", "choices"}
            if set(self.args) - allowed:
                raise ValueError("request_user action has unsupported args")
            question = self.args.get("question")
            if not isinstance(question, str) or not question.strip():
                raise ValueError("request_user actions require a non-empty question")
            choices = self.args.get("choices", [])
            if not isinstance(choices, list) or not all(
                isinstance(choice, str) for choice in choices
            ):
                raise ValueError("request_user choices must be a string list")
        return self


class GuardrailDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: GuardrailDecisionType
    rules: list[str] = Field(default_factory=list)
    message: str
    rewritten_action: Action | None = None


class FeedbackSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: FeedbackType
    severity: Literal["info", "warning", "error"]
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "failed", "blocked", "needs_approval", "timeout"]
    stdout_summary: str = ""
    stderr_summary: str = ""
    artifacts: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = 0
    feedback: list[FeedbackSignal] = Field(default_factory=list)
    redactions: list[str] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    run_id: str
    action_id: str
    action: Action
    state: ApprovalState
    rules: list[str]
    reason: str
    step_index: int = 0
    feedback: list[FeedbackSignal] = Field(default_factory=list)
    reviewer: str | None = None
    reviewer_reason: str | None = None
    execution_result: ToolResult | None = None


class MemoryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    scope: str
    kind: Literal["event", "summary"]
    tags: list[str]
    content: str
    source_run_id: str | None = None
    confidence: float = 1.0
    sensitive: bool = False
