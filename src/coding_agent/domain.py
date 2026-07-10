from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


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
