# CodingAgent Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-coded coding-agent harness with deterministic guardrails, feedback loop, memory, tool dispatch, mock-first demos, full WebUI, Docker distribution, and CI.

**Architecture:** The implementation is a Python package under `src/coding_agent` with a FastAPI app, Typer CLI, SQLite-backed audit/memory store, deterministic mock LLM, optional OpenAI-compatible real LLM provider, and React/Vite frontend under `frontend`. The first vertical slice is backend core plus mock demo; WebUI, credentials, Docker, and CI are added after the core mechanisms are testable.

**Tech Stack:** Python 3.11+, Pydantic v2, FastAPI, Typer, pytest, SQLite, keyring, OpenAI-compatible HTTP client, React, Vite, TypeScript, Vitest, Docker Compose, GitHub Actions, GitLab CI.

## Global Constraints

- Default validation and CI must use mock LLM; real LLM is optional and disabled by default.
- `OPENAI_BASE_URL` default is `https://njusehub.info/v1`; expected real model is `glm-5.2`.
- Public deployment defaults: `LLM_MODE=mock`, `ENABLE_REAL_LLM=false`, `ADMIN_PASSWORD` required.
- Guardrail logic must be deterministic code, never prompt-only.
- No real provider token, `.env`, local database, exported run logs, or runtime state may be committed.
- WebUI first screen is an operational dashboard, not a marketing landing page.
- Every implementation task uses TDD: write failing test, run red, implement minimal code, run green, commit.
- Cold-start validation is still required after this plan is reviewed; do not implement code before cold-start validation is complete.

## 执行状态与提交证据

原始实现计划已经完成，关键提交如下：

- [x] Task 1：领域模型，`4c510f9`。
- [x] Task 2：策略与 Action Parser，`325156f`。
- [x] Task 3：SQLite Store 与 EventBus，`5332a36`。
- [x] Task 4：Guardrail、脱敏和 HITL，`3d1a07e`。
- [x] Task 5：工具分发与安全文件工具，`3501b46`。
- [x] Task 6：反馈解析，`7c76f1a`。
- [x] Task 7：命令工具与示例工程，`6e53ec2`。
- [x] Task 8：确定性 Memory，`cc65025`。
- [x] Task 9：Mock LLM 与 AgentLoop，`ac5137c`。
- [x] Task 10：CLI 与演示，`3a2de65`。
- [x] Task 11：FastAPI 与 SSE，`b829da6`。
- [x] Task 12：前端类型与 API Client，`7132695`。
- [x] Task 13：WebUI Dashboard，`3af238d`。
- [x] Task 14：真实 LLM Gate，`47aee7c`。
- [x] Task 15：Docker、CI 与部署骨架，`392672d`。

2026-07-11 工程交付增量：

- [x] 安全凭据生命周期和全链路脱敏，`e57a2f9..b078521`。
- [x] 管理员签名会话，`9a542b4`。
- [x] 持久化运行生命周期与恢复，`5473d04`。
- [x] 真实模型驱动同一 AgentLoop，`35111d0`。
- [x] 实时 SSE 与持久化审批恢复，`0c2b9d7`。
- [x] 完整 Mock/Real WebUI，`79361b5`。
- [x] 生产 Compose、Nginx、CI 与 GHCR 工作流，`90a00ff`。
- [x] 最终总回归、浏览器验收和课程证据更新，`e60a557`。

2026-07-12 最终交付闭环：

- [x] 真实 LLM calculator 工具反馈与审批链路修复，通过 [PR #4](https://github.com/xhy-nju/CodingAgent/pull/4) 合并。
- [x] HTTP 临时演示与 HTTPS 正式部署的 Cookie 配置分离，通过 [PR #5](https://github.com/xhy-nju/CodingAgent/pull/5) 合并。
- [x] 发布 `ghcr.io/xhy-nju/coding-agent:1.0.1` 并完成真实 `glm-5.2` 隔离验收。
- [x] 阿里云公网 WebUI 部署到 [http://47.96.99.58/](http://47.96.99.58/)。
- [x] 演示视频通过 [PR #6](https://github.com/xhy-nju/CodingAgent/pull/6) 提交到仓库。
- [x] 最新 `main` CI [#29197433911](https://github.com/xhy-nju/CodingAgent/actions/runs/29197433911) 全部通过。

---

## File Structure

Create this structure during the tasks below:

```text
.
├── pyproject.toml
├── .gitignore
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── .gitlab-ci.yml
├── .github/workflows/ci.yml
├── config/policies/strict_demo.json
├── config/policies/balanced_dev.json
├── demos/sample_workspace/calculator.py
├── demos/sample_workspace/test_calculator.py
├── scripts/export_run.py
├── src/coding_agent/__init__.py
├── src/coding_agent/__main__.py
├── src/coding_agent/domain.py
├── src/coding_agent/action_parser.py
├── src/coding_agent/policies.py
├── src/coding_agent/redaction.py
├── src/coding_agent/guardrails.py
├── src/coding_agent/approvals.py
├── src/coding_agent/store.py
├── src/coding_agent/events.py
├── src/coding_agent/feedback.py
├── src/coding_agent/memory.py
├── src/coding_agent/llm.py
├── src/coding_agent/agent_loop.py
├── src/coding_agent/cli.py
├── src/coding_agent/api.py
├── src/coding_agent/tools/base.py
├── src/coding_agent/tools/files.py
├── src/coding_agent/tools/commands.py
├── src/coding_agent/tools/dispatcher.py
├── tests/test_domain.py
├── tests/test_action_parser.py
├── tests/test_guardrails.py
├── tests/test_approvals.py
├── tests/test_feedback.py
├── tests/test_memory.py
├── tests/test_tools.py
├── tests/test_agent_loop.py
├── tests/test_cli.py
├── tests/test_api.py
├── frontend/package.json
├── frontend/index.html
├── frontend/vite.config.ts
├── frontend/tsconfig.json
├── frontend/src/main.tsx
├── frontend/src/App.tsx
├── frontend/src/api.ts
├── frontend/src/types.ts
├── frontend/src/styles.css
├── frontend/src/App.test.tsx
└── frontend/src/api.test.ts
```

Responsibilities:

- `domain.py`: shared immutable Pydantic models and enums.
- `action_parser.py`: strict JSON action parsing and schema feedback.
- `policies.py`: policy profile loading and typed policy models.
- `guardrails.py`: deterministic allow/deny/approval/rewrite decisions.
- `approvals.py`: HITL approval state machine.
- `store.py`: SQLite persistence for runs, events, approvals, and memory.
- `events.py`: append-only event bus used by API SSE and CLI reports.
- `feedback.py`: parse pytest, command, guardrail, approval, timeout, and schema results.
- `memory.py`: deterministic memory write/search over SQLite.
- `tools/*`: tool specs, safe file tools, command/test tools, dispatcher.
- `llm.py`: mock provider and optional OpenAI-compatible real provider.
- `agent_loop.py`: orchestration loop connecting LLM, parser, guardrails, tools, feedback, memory.
- `api.py`: FastAPI REST, SSE, and admin auth.
- `cli.py`: Typer commands for demos, run export, and credential status.
- `frontend/*`: dashboard, demo center, run detail, approval queue, memory, policies, credentials, settings.

---

### Task 1: Python Project Skeleton And Domain Models

**Files:**
- Create: `pyproject.toml`
- Create: `src/coding_agent/__init__.py`
- Create: `src/coding_agent/domain.py`
- Test: `tests/test_domain.py`

**Interfaces:**
- Produces: `Action`, `ActionKind`, `GuardrailDecision`, `GuardrailDecisionType`, `FeedbackSignal`, `FeedbackType`, `ToolResult`, `RunStatus`, `ApprovalRequest`, `ApprovalState`, `MemoryRecord`.
- Later tasks import these exact names from `coding_agent.domain`.

- [x] **Step 1: Write the failing domain tests**

Create `tests/test_domain.py`:

```python
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
    approval = ApprovalRequest(
        id="approval-1",
        action_id="action-1",
        state=ApprovalState.PENDING,
        rules=["command.needs_human"],
        reason="command requires approval",
    )

    assert approval.state is ApprovalState.PENDING
```

- [x] **Step 2: Run the domain tests and verify red**

Run: `pytest tests/test_domain.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'coding_agent'` or import errors for missing models.

- [x] **Step 3: Add packaging and domain models**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "coding-agent"
version = "0.1.0"
description = "Spec-driven coding agent harness with deterministic guardrails"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.30.0",
  "typer>=0.12.0",
  "pydantic>=2.7.0",
  "httpx>=0.27.0",
  "keyring>=25.0.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2.0",
  "pytest-asyncio>=0.23.0",
  "ruff>=0.5.0",
]

[project.scripts]
coding-agent = "coding_agent.cli:app"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
src = ["src", "tests"]
```

Create `src/coding_agent/__init__.py`:

```python
__all__ = ["__version__"]
__version__ = "0.1.0"
```

Create `src/coding_agent/domain.py`:

```python
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
    action_id: str
    state: ApprovalState
    rules: list[str]
    reason: str
    reviewer: str | None = None
    reviewer_reason: str | None = None


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
```

- [x] **Step 4: Run the domain tests and verify green**

Run: `pytest tests/test_domain.py -v`

Expected: PASS with `4 passed`.

- [x] **Step 5: Commit Task 1**

Run:

```bash
git add pyproject.toml src/coding_agent/__init__.py src/coding_agent/domain.py tests/test_domain.py
git commit -m "feat: add core domain models"
```

### Task 2: Policy Profiles And Strict Action Parser

**Files:**
- Create: `config/policies/strict_demo.json`
- Create: `config/policies/balanced_dev.json`
- Create: `src/coding_agent/policies.py`
- Create: `src/coding_agent/action_parser.py`
- Test: `tests/test_action_parser.py`

**Interfaces:**
- Consumes: `Action`, `FeedbackSignal`, `FeedbackType` from `coding_agent.domain`.
- Produces: `PolicyProfile`, `load_policy(name: str, config_dir: Path) -> PolicyProfile`, `ParseResult`, `parse_action(raw: str) -> ParseResult`.

- [x] **Step 1: Write failing parser and policy tests**

Create `tests/test_action_parser.py`:

```python
from pathlib import Path

from coding_agent.action_parser import parse_action
from coding_agent.domain import ActionKind, FeedbackType
from coding_agent.policies import load_policy


def test_parse_valid_tool_action() -> None:
    result = parse_action(
        '{"kind":"tool","tool":"read_file","args":{"path":"calculator.py"},'
        '"reason":"inspect","expectation":"read file"}'
    )

    assert result.ok is True
    assert result.action is not None
    assert result.action.kind is ActionKind.TOOL
    assert result.action.tool == "read_file"


def test_parse_invalid_json_returns_schema_feedback() -> None:
    result = parse_action("not json")

    assert result.ok is False
    assert result.feedback is not None
    assert result.feedback.type is FeedbackType.SCHEMA_ERROR
    assert "valid JSON" in result.feedback.summary


def test_parse_unknown_kind_returns_schema_feedback() -> None:
    result = parse_action(
        '{"kind":"unknown","reason":"x","expectation":"y","args":{}}'
    )

    assert result.ok is False
    assert result.feedback is not None
    assert result.feedback.type is FeedbackType.SCHEMA_ERROR


def test_load_strict_policy() -> None:
    policy = load_policy("strict_demo", Path("config/policies"))

    assert policy.name == "strict_demo"
    assert "read_file" in policy.allowed_tools
    assert "rm" in policy.denied_command_fragments
```

- [x] **Step 2: Run parser tests and verify red**

Run: `pytest tests/test_action_parser.py -v`

Expected: FAIL with import errors for `coding_agent.action_parser` and `coding_agent.policies`.

- [x] **Step 3: Create policy files**

Create `config/policies/strict_demo.json`:

```json
{
  "name": "strict_demo",
  "allowed_tools": ["list_files", "read_file", "write_file", "run_tests", "run_command", "memory_search", "memory_write"],
  "allowed_command_prefixes": [["python", "-m", "pytest"], ["pytest"]],
  "denied_command_fragments": ["blocked-delete", "rm", "del", "blocked-remove-item", "format", "curl", "wget", "ssh", "scp", "docker", "kubectl"],
  "protected_path_fragments": [".env", "id_rsa", "id_ed25519", ".ssh", ".aws", ".git", "credentials"],
  "max_file_bytes": 20000,
  "tool_timeout_seconds": 30,
  "require_approval_tools": ["run_command"]
}
```

Create `config/policies/balanced_dev.json`:

```json
{
  "name": "balanced_dev",
  "allowed_tools": ["list_files", "read_file", "write_file", "run_tests", "run_lint", "run_command", "memory_search", "memory_write"],
  "allowed_command_prefixes": [["python", "-m", "pytest"], ["pytest"], ["python", "-m", "ruff"], ["ruff", "check"]],
  "denied_command_fragments": ["blocked-delete --recursive", "blocked-remove-item --recursive", "format", "ssh", "scp", "kubectl delete", "docker push"],
  "protected_path_fragments": [".env", "id_rsa", "id_ed25519", ".ssh", ".aws", ".git", "credentials"],
  "max_file_bytes": 50000,
  "tool_timeout_seconds": 60,
  "require_approval_tools": []
}
```

- [x] **Step 4: Implement policy loader and action parser**

Create `src/coding_agent/policies.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class PolicyProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    allowed_tools: list[str]
    allowed_command_prefixes: list[list[str]]
    denied_command_fragments: list[str]
    protected_path_fragments: list[str]
    max_file_bytes: int
    tool_timeout_seconds: int
    require_approval_tools: list[str]


def load_policy(name: str, config_dir: Path) -> PolicyProfile:
    path = config_dir / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Policy profile not found: {path}")
    return PolicyProfile.model_validate_json(path.read_text(encoding="utf-8"))
```

Create `src/coding_agent/action_parser.py`:

```python
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from coding_agent.domain import Action, FeedbackSignal, FeedbackType


class ParseResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ok: bool
    action: Action | None = None
    feedback: FeedbackSignal | None = None
    raw: str


def _schema_error(summary: str, raw: str, details: dict[str, Any] | None = None) -> ParseResult:
    return ParseResult(
        ok=False,
        raw=raw,
        feedback=FeedbackSignal(
            type=FeedbackType.SCHEMA_ERROR,
            severity="error",
            summary=summary,
            details=details or {},
        ),
    )


def parse_action(raw: str) -> ParseResult:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return _schema_error("LLM output must be valid JSON", raw, {"error": str(exc)})

    if not isinstance(payload, dict):
        return _schema_error("LLM output JSON must be an object", raw)

    try:
        action = Action.model_validate(payload)
    except ValidationError as exc:
        return _schema_error("LLM action failed schema validation", raw, {"errors": exc.errors()})

    if action.kind == "tool" and not action.tool:
        return _schema_error("Tool action must include tool name", raw)

    return ParseResult(ok=True, raw=raw, action=action)
```

- [x] **Step 5: Run parser tests and verify green**

Run: `pytest tests/test_action_parser.py -v`

Expected: PASS with `4 passed`.

- [x] **Step 6: Commit Task 2**

Run:

```bash
git add config/policies src/coding_agent/policies.py src/coding_agent/action_parser.py tests/test_action_parser.py
git commit -m "feat: add policies and action parser"
```

### Task 3: SQLite Store And Event Bus

**Files:**
- Create: `src/coding_agent/store.py`
- Create: `src/coding_agent/events.py`
- Test: `tests/test_store_events.py`

**Interfaces:**
- Consumes: `RunStatus`, `FeedbackSignal`, `MemoryRecord`.
- Produces: `SqliteStore(db_path: Path)`, `EventBus(store: SqliteStore)`, `create_run(task, workspace, policy_profile, llm_mode) -> str`, `append_event(run_id, event_type, payload) -> None`, `list_events(run_id) -> list[dict]`.

- [x] **Step 1: Write failing store tests**

Create `tests/test_store_events.py`:

```python
from pathlib import Path

from coding_agent.events import EventBus
from coding_agent.store import SqliteStore


def test_create_run_and_append_event(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "agent.db")
    bus = EventBus(store)

    run_id = store.create_run(
        task="fix calculator",
        workspace="demos/sample_workspace",
        policy_profile="strict_demo",
        llm_mode="mock",
    )
    bus.append_event(run_id, "run.created", {"task": "fix calculator"})

    events = bus.list_events(run_id)
    assert len(events) == 1
    assert events[0]["event_type"] == "run.created"
    assert events[0]["payload"]["task"] == "fix calculator"


def test_memory_round_trip(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "agent.db")
    store.write_memory(
        scope="project",
        kind="summary",
        tags=["policy", "strict_demo"],
        content="strict demo blocks recursive delete",
        source_run_id=None,
        confidence=1.0,
        sensitive=False,
    )

    rows = store.search_memory(tags=["policy"], query="recursive")
    assert rows[0].content == "strict demo blocks recursive delete"
```

- [x] **Step 2: Run store tests and verify red**

Run: `pytest tests/test_store_events.py -v`

Expected: FAIL with import errors for `coding_agent.store` and `coding_agent.events`.

- [x] **Step 3: Implement SQLite store and event bus**

Create `src/coding_agent/store.py` with a minimal `sqlite3` implementation:

```python
from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from coding_agent.domain import MemoryRecord, RunStatus


class SqliteStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                create table if not exists runs (
                    id text primary key,
                    task text not null,
                    workspace text not null,
                    policy_profile text not null,
                    llm_mode text not null,
                    status text not null,
                    created_at text default current_timestamp,
                    finished_at text
                );
                create table if not exists events (
                    id text primary key,
                    run_id text not null,
                    event_type text not null,
                    payload_json text not null,
                    created_at text default current_timestamp
                );
                create table if not exists memory (
                    id text primary key,
                    scope text not null,
                    kind text not null,
                    tags_json text not null,
                    content text not null,
                    source_run_id text,
                    confidence real not null,
                    sensitive integer not null,
                    created_at text default current_timestamp
                );
                """
            )

    def create_run(self, task: str, workspace: str, policy_profile: str, llm_mode: str) -> str:
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        with self._connect() as conn:
            conn.execute(
                "insert into runs(id, task, workspace, policy_profile, llm_mode, status) values (?, ?, ?, ?, ?, ?)",
                (run_id, task, workspace, policy_profile, llm_mode, RunStatus.CREATED.value),
            )
        return run_id

    def update_run_status(self, run_id: str, status: RunStatus) -> None:
        with self._connect() as conn:
            conn.execute("update runs set status = ? where id = ?", (status.value, run_id))

    def append_event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "insert into events(id, run_id, event_type, payload_json) values (?, ?, ?, ?)",
                (f"event-{uuid.uuid4().hex[:12]}", run_id, event_type, json.dumps(payload, ensure_ascii=False)),
            )

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "select id, event_type, payload_json, created_at from events where run_id = ? order by created_at, id",
                (run_id,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def write_memory(
        self,
        scope: str,
        kind: str,
        tags: list[str],
        content: str,
        source_run_id: str | None,
        confidence: float,
        sensitive: bool,
    ) -> str:
        memory_id = f"mem-{uuid.uuid4().hex[:12]}"
        with self._connect() as conn:
            conn.execute(
                "insert into memory(id, scope, kind, tags_json, content, source_run_id, confidence, sensitive) values (?, ?, ?, ?, ?, ?, ?, ?)",
                (memory_id, scope, kind, json.dumps(tags), content, source_run_id, confidence, int(sensitive)),
            )
        return memory_id

    def search_memory(self, tags: list[str], query: str) -> list[MemoryRecord]:
        with self._connect() as conn:
            rows = conn.execute("select * from memory where sensitive = 0 order by created_at desc").fetchall()
        lowered = query.lower()
        result: list[MemoryRecord] = []
        for row in rows:
            row_tags = json.loads(row["tags_json"])
            tag_match = not tags or any(tag in row_tags for tag in tags)
            query_match = not query or lowered in row["content"].lower()
            if tag_match and query_match:
                result.append(
                    MemoryRecord(
                        id=row["id"],
                        scope=row["scope"],
                        kind=row["kind"],
                        tags=row_tags,
                        content=row["content"],
                        source_run_id=row["source_run_id"],
                        confidence=float(row["confidence"]),
                        sensitive=bool(row["sensitive"]),
                    )
                )
        return result
```

Create `src/coding_agent/events.py`:

```python
from __future__ import annotations

from typing import Any

from coding_agent.store import SqliteStore


class EventBus:
    def __init__(self, store: SqliteStore) -> None:
        self.store = store

    def append_event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self.store.append_event(run_id, event_type, payload)

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        return self.store.list_events(run_id)
```

- [x] **Step 4: Run store tests and verify green**

Run: `pytest tests/test_store_events.py -v`

Expected: PASS with `2 passed`.

- [x] **Step 5: Commit Task 3**

Run:

```bash
git add src/coding_agent/store.py src/coding_agent/events.py tests/test_store_events.py
git commit -m "feat: add sqlite audit store"
```

### Task 4: Guardrails, Redaction, And HITL Approval State Machine

**Files:**
- Create: `src/coding_agent/redaction.py`
- Create: `src/coding_agent/guardrails.py`
- Create: `src/coding_agent/approvals.py`
- Test: `tests/test_guardrails.py`
- Test: `tests/test_approvals.py`

**Interfaces:**
- Consumes: `Action`, `GuardrailDecision`, `PolicyProfile`, `ToolResult`.
- Produces: `redact_secrets(text: str) -> tuple[str, list[str]]`, `GuardrailEngine(policy: PolicyProfile, workspace: Path)`, `evaluate(action: Action) -> GuardrailDecision`, `ApprovalService` with `create`, `approve_once`, `reject`, `request_revision`, `cancel`.

**Prerequisites:**
- Complete Task 1 and Task 2 first, or create their exact prerequisite files when running this task as a cold-start probe.
- A cold-start agent may create Task 1/2 dependency files only to make Task 4 runnable; those files are validation scaffolding unless formal implementation has reached those tasks in order.
- Task 4 implements provider-token redaction as the minimal redaction slice. Broader HTTP header and generic credential redaction remains covered by later credential/API tasks.

- [x] **Step 1: Write failing guardrail and approval tests**

Create `tests/test_guardrails.py`:

```python
from pathlib import Path

from coding_agent.domain import Action, ActionKind, GuardrailDecisionType
from coding_agent.guardrails import GuardrailEngine
from coding_agent.policies import load_policy
from coding_agent.redaction import redact_secrets


def test_denies_path_outside_workspace(tmp_path: Path) -> None:
    policy = load_policy("strict_demo", Path("config/policies"))
    engine = GuardrailEngine(policy=policy, workspace=tmp_path)
    action = Action(
        kind=ActionKind.TOOL,
        tool="read_file",
        args={"path": "../outside.txt"},
        reason="read outside",
        expectation="should be blocked",
    )

    decision = engine.evaluate(action)

    assert decision.decision is GuardrailDecisionType.DENY
    assert "path.outside_workspace" in decision.rules


def test_run_command_requires_approval_in_strict_demo(tmp_path: Path) -> None:
    policy = load_policy("strict_demo", Path("config/policies"))
    engine = GuardrailEngine(policy=policy, workspace=tmp_path)
    action = Action(
        kind=ActionKind.TOOL,
        tool="run_command",
        args={"command": ["pytest"]},
        reason="manual shell",
        expectation="approval required",
    )

    decision = engine.evaluate(action)

    assert decision.decision is GuardrailDecisionType.NEEDS_APPROVAL
    assert "tool.requires_approval" in decision.rules


def test_denies_recursive_delete_fragment(tmp_path: Path) -> None:
    policy = load_policy("balanced_dev", Path("config/policies"))
    engine = GuardrailEngine(policy=policy, workspace=tmp_path)
    action = Action(
        kind=ActionKind.TOOL,
        tool="run_command",
        args={"command": ["blocked-delete", "--recursive", "."]},
        reason="blocked cleanup",
        expectation="blocked",
    )

    decision = engine.evaluate(action)

    assert decision.decision is GuardrailDecisionType.DENY
    assert "command.denied_fragment" in decision.rules


def test_redacts_provider_token_like_values() -> None:
    redacted, labels = redact_secrets("token=demo-redaction-value-123456")

    assert "demo-redaction-value-123456" not in redacted
    assert labels == ["provider_token"]
```

Create `tests/test_approvals.py`:

```python
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
```

- [x] **Step 2: Run guardrail tests and verify red**

Run: `pytest tests/test_guardrails.py tests/test_approvals.py -v`

Expected: FAIL with import errors for guardrails, redaction, and approvals modules.

- [x] **Step 3: Implement redaction, guardrails, and approvals**

Create `src/coding_agent/redaction.py`:

```python
from __future__ import annotations

import re

SECRET_PATTERNS = [
    ("provider_token", re.compile(r"demo-token-[A-Za-z0-9_-]{10,}")),
    ("provider_token", re.compile(r"token=[A-Za-z0-9._=-]{12,}", re.IGNORECASE)),
    ("provider_token", re.compile(r"Token\s+[A-Za-z0-9._-]{12,}", re.IGNORECASE)),
]


def redact_secrets(text: str) -> tuple[str, list[str]]:
    labels: list[str] = []
    redacted = text
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(redacted):
            labels.append(label)
            redacted = pattern.sub(f"[{label}:redacted]", redacted)
    return redacted, labels
```

Create `src/coding_agent/guardrails.py`:

```python
from __future__ import annotations

from pathlib import Path

from coding_agent.domain import Action, GuardrailDecision, GuardrailDecisionType
from coding_agent.policies import PolicyProfile


class GuardrailEngine:
    def __init__(self, policy: PolicyProfile, workspace: Path) -> None:
        self.policy = policy
        self.workspace = workspace.resolve()

    def evaluate(self, action: Action) -> GuardrailDecision:
        rules: list[str] = []

        if action.tool not in self.policy.allowed_tools:
            return GuardrailDecision(
                decision=GuardrailDecisionType.DENY,
                rules=["tool.not_allowed"],
                message=f"Tool is not allowed by policy: {action.tool}",
            )

        path_value = action.args.get("path") or action.args.get("target")
        if isinstance(path_value, str) and self._path_is_unsafe(path_value):
            rules.append("path.outside_workspace")

        command = action.args.get("command")
        if isinstance(command, list):
            command_text = " ".join(str(part) for part in command)
            if any(fragment in command_text for fragment in self.policy.denied_command_fragments):
                rules.append("command.denied_fragment")
            if action.tool == "run_command" and not self._command_prefix_allowed(command):
                rules.append("command.prefix_not_allowed")

        for value in action.args.values():
            if isinstance(value, str) and any(fragment in value for fragment in self.policy.protected_path_fragments):
                rules.append("path.protected_fragment")

        if rules:
            return GuardrailDecision(
                decision=GuardrailDecisionType.DENY,
                rules=sorted(set(rules)),
                message="Action violates guardrail policy",
            )

        if action.tool in self.policy.require_approval_tools:
            return GuardrailDecision(
                decision=GuardrailDecisionType.NEEDS_APPROVAL,
                rules=["tool.requires_approval"],
                message="Tool requires human approval in this policy",
            )

        return GuardrailDecision(
            decision=GuardrailDecisionType.ALLOW,
            rules=[],
            message="Action allowed",
        )

    def _path_is_unsafe(self, path_value: str) -> bool:
        candidate = (self.workspace / path_value).resolve()
        return not candidate.is_relative_to(self.workspace)

    def _command_prefix_allowed(self, command: list[object]) -> bool:
        normalized = [str(part) for part in command]
        return any(normalized[: len(prefix)] == prefix for prefix in self.policy.allowed_command_prefixes)
```

Create `src/coding_agent/approvals.py`:

```python
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
        updated = current.model_copy(update={"state": state, "reviewer": reviewer, "reviewer_reason": reason})
        self._requests[request_id] = updated
        return updated
```

- [x] **Step 4: Run guardrail and approval tests and verify green**

Run: `pytest tests/test_guardrails.py tests/test_approvals.py -v`

Expected: PASS with `5 passed`.

- [x] **Step 5: Commit Task 4**

Run:

```bash
git add src/coding_agent/redaction.py src/coding_agent/guardrails.py src/coding_agent/approvals.py tests/test_guardrails.py tests/test_approvals.py
git commit -m "feat: add deterministic guardrails and approvals"
```

### Task 5: Tool Dispatcher And Safe File Tools

**Files:**
- Create: `src/coding_agent/tools/base.py`
- Create: `src/coding_agent/tools/files.py`
- Create: `src/coding_agent/tools/dispatcher.py`
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: `Action`, `ToolResult`, `GuardrailEngine`.
- Produces: `ToolSpec`, `ToolContext`, `ToolDispatcher.dispatch(action: Action) -> ToolResult`, file tools `list_files`, `read_file`, `write_file`.

- [x] **Step 1: Write failing file tool tests**

Create `tests/test_tools.py`:

```python
from pathlib import Path

from coding_agent.domain import Action, ActionKind
from coding_agent.guardrails import GuardrailEngine
from coding_agent.policies import load_policy
from coding_agent.tools.dispatcher import build_default_dispatcher


def test_read_file_inside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "calculator.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    policy = load_policy("strict_demo", Path("config/policies"))
    dispatcher = build_default_dispatcher(GuardrailEngine(policy, workspace), workspace, policy)

    result = dispatcher.dispatch(
        Action(
            kind=ActionKind.TOOL,
            tool="read_file",
            args={"path": "calculator.py"},
            reason="read file",
            expectation="source text",
        )
    )

    assert result.status == "ok"
    assert "return a + b" in result.artifacts["content"]


def test_write_file_returns_diff_summary(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    policy = load_policy("strict_demo", Path("config/policies"))
    dispatcher = build_default_dispatcher(GuardrailEngine(policy, workspace), workspace, policy)

    result = dispatcher.dispatch(
        Action(
            kind=ActionKind.TOOL,
            tool="write_file",
            args={"path": "note.txt", "content": "hello\n"},
            reason="write file",
            expectation="file exists",
        )
    )

    assert result.status == "ok"
    assert (workspace / "note.txt").read_text(encoding="utf-8") == "hello\n"
    assert result.artifacts["diff_summary"] == "created note.txt"


def test_dispatcher_blocks_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    policy = load_policy("strict_demo", Path("config/policies"))
    dispatcher = build_default_dispatcher(GuardrailEngine(policy, workspace), workspace, policy)

    result = dispatcher.dispatch(
        Action(
            kind=ActionKind.TOOL,
            tool="read_file",
            args={"path": "../outside.txt"},
            reason="read outside",
            expectation="blocked",
        )
    )

    assert result.status == "blocked"
    assert result.feedback[0].type == "guardrail_blocked"
```

- [x] **Step 2: Run file tool tests and verify red**

Run: `pytest tests/test_tools.py -v`

Expected: FAIL with import errors for `coding_agent.tools.dispatcher`.

- [x] **Step 3: Implement base tool abstractions**

Create `src/coding_agent/tools/base.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from coding_agent.domain import ToolResult
from coding_agent.policies import PolicyProfile


class ToolContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    workspace: Path
    policy: PolicyProfile


class ToolSpec(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    handler: Callable[[dict[str, Any], ToolContext], ToolResult]
```

- [x] **Step 4: Implement safe file tools**

Create `src/coding_agent/tools/files.py`:

```python
from __future__ import annotations

from pathlib import Path

from coding_agent.domain import ToolResult
from coding_agent.tools.base import ToolContext


IGNORED_PARTS = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}


def _resolve_inside(workspace: Path, relative_path: str) -> Path:
    candidate = (workspace / relative_path).resolve()
    root = workspace.resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("path outside workspace")
    return candidate


def list_files(args: dict[str, object], context: ToolContext) -> ToolResult:
    files: list[str] = []
    for path in sorted(context.workspace.rglob("*")):
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        if path.is_file():
            files.append(path.relative_to(context.workspace).as_posix())
    return ToolResult(status="ok", artifacts={"files": files})


def read_file(args: dict[str, object], context: ToolContext) -> ToolResult:
    relative = str(args["path"])
    path = _resolve_inside(context.workspace, relative)
    content = path.read_text(encoding="utf-8")
    if len(content.encode("utf-8")) > context.policy.max_file_bytes:
        return ToolResult(status="failed", stderr_summary=f"file too large: {relative}")
    return ToolResult(status="ok", artifacts={"path": relative, "content": content})


def write_file(args: dict[str, object], context: ToolContext) -> ToolResult:
    relative = str(args["path"])
    content = str(args["content"])
    path = _resolve_inside(context.workspace, relative)
    existed = path.exists()
    before = path.read_text(encoding="utf-8") if existed else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if existed:
        diff_summary = f"updated {relative}: {len(before.splitlines())} lines -> {len(content.splitlines())} lines"
    else:
        diff_summary = f"created {relative}"
    return ToolResult(status="ok", artifacts={"path": relative, "diff_summary": diff_summary})
```

- [x] **Step 5: Implement dispatcher with guardrail feedback**

Create `src/coding_agent/tools/dispatcher.py`:

```python
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
```

- [x] **Step 6: Run file tool tests and verify green**

Run: `pytest tests/test_tools.py -v`

Expected: PASS with `3 passed`.

- [x] **Step 7: Commit Task 5**

Run:

```bash
git add src/coding_agent/tools tests/test_tools.py
git commit -m "feat: add guarded file tools"
```

### Task 6: Feedback Parser For Tests, Commands, And Guardrails

**Files:**
- Create: `src/coding_agent/feedback.py`
- Test: `tests/test_feedback.py`

**Interfaces:**
- Consumes: `ToolResult`, `FeedbackSignal`, `FeedbackType`.
- Produces: `parse_pytest_output(exit_code: int, stdout: str, stderr: str) -> FeedbackSignal`, `feedback_from_tool_result(result: ToolResult) -> list[FeedbackSignal]`.

- [x] **Step 1: Write failing feedback tests**

Create `tests/test_feedback.py`:

```python
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
```

- [x] **Step 2: Run feedback tests and verify red**

Run: `pytest tests/test_feedback.py -v`

Expected: FAIL with import error for `coding_agent.feedback`.

- [x] **Step 3: Implement feedback parser**

Create `src/coding_agent/feedback.py`:

```python
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
```

- [x] **Step 4: Run feedback tests and verify green**

Run: `pytest tests/test_feedback.py -v`

Expected: PASS with `3 passed`.

- [x] **Step 5: Commit Task 6**

Run:

```bash
git add src/coding_agent/feedback.py tests/test_feedback.py
git commit -m "feat: parse objective feedback signals"
```

### Task 7: Command Tools And Built-In Sample Workspace

**Files:**
- Modify: `src/coding_agent/tools/commands.py`
- Modify: `src/coding_agent/tools/dispatcher.py`
- Create: `demos/sample_workspace/calculator.py`
- Create: `demos/sample_workspace/test_calculator.py`
- Test: `tests/test_command_tools.py`

**Interfaces:**
- Consumes: `parse_pytest_output`, `ToolContext`, `ToolResult`.
- Produces: `run_tests(args, context) -> ToolResult`, `run_command(args, context) -> ToolResult`.

- [x] **Step 1: Write failing command tool tests**

Create `tests/test_command_tools.py`:

```python
from pathlib import Path

from coding_agent.domain import Action, ActionKind, FeedbackType
from coding_agent.guardrails import GuardrailEngine
from coding_agent.policies import load_policy
from coding_agent.tools.dispatcher import build_default_dispatcher


def test_run_tests_produces_test_failed_feedback(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "test_sample.py").write_text("def test_fail():\n    assert 1 == 2\n", encoding="utf-8")
    policy = load_policy("strict_demo", Path("config/policies"))
    dispatcher = build_default_dispatcher(GuardrailEngine(policy, workspace), workspace, policy)

    result = dispatcher.dispatch(
        Action(
            kind=ActionKind.TOOL,
            tool="run_tests",
            args={"target": "."},
            reason="run tests",
            expectation="failure feedback",
        )
    )

    assert result.status == "failed"
    assert result.feedback[0].type is FeedbackType.TEST_FAILED


def test_sample_workspace_starts_with_failing_test() -> None:
    workspace = Path("demos/sample_workspace")
    assert (workspace / "calculator.py").exists()
    assert (workspace / "test_calculator.py").exists()
```

- [x] **Step 2: Run command tool tests and verify red**

Run: `pytest tests/test_command_tools.py -v`

Expected: FAIL because `run_tests` is not registered and sample workspace files do not exist.

- [x] **Step 3: Create sample workspace**

Create `demos/sample_workspace/calculator.py`:

```python
def add(a: int, b: int) -> int:
    return a - b
```

Create `demos/sample_workspace/test_calculator.py`:

```python
from calculator import add


def test_add_positive_numbers() -> None:
    assert add(2, 3) == 5


def test_add_negative_number() -> None:
    assert add(2, -3) == -1
```

- [x] **Step 4: Implement command tools and register them**

Create `src/coding_agent/tools/commands.py`:

```python
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
```

Modify `build_default_dispatcher` in `src/coding_agent/tools/dispatcher.py` to register command tools:

```python
from coding_agent.tools.commands import run_command, run_tests

# inside build_default_dispatcher after file tool registrations
    dispatcher.register(ToolSpec(name="run_tests", description="Run pytest in workspace", handler=run_tests))
    dispatcher.register(ToolSpec(name="run_command", description="Run a guarded command", handler=run_command))
```

- [x] **Step 5: Run command tool tests and verify green**

Run: `pytest tests/test_command_tools.py -v`

Expected: PASS with `2 passed`.

- [x] **Step 6: Commit Task 7**

Run:

```bash
git add src/coding_agent/tools/commands.py src/coding_agent/tools/dispatcher.py demos/sample_workspace tests/test_command_tools.py
git commit -m "feat: add command tools and sample workspace"
```

### Task 8: Deterministic Memory Search And Memory Tools

**Files:**
- Create: `src/coding_agent/memory.py`
- Modify: `src/coding_agent/tools/dispatcher.py`
- Modify: `src/coding_agent/tools/base.py`
- Test: `tests/test_memory.py`

**Interfaces:**
- Consumes: `SqliteStore`, `MemoryRecord`, `ToolContext`.
- Produces: `MemoryService.write_summary(...)`, `MemoryService.search(...)`, dispatcher tools `memory_search` and `memory_write`.

- [x] **Step 1: Write failing memory tests**

Create `tests/test_memory.py`:

```python
from pathlib import Path

from coding_agent.memory import MemoryService
from coding_agent.store import SqliteStore


def test_memory_search_is_tag_and_keyword_based(tmp_path: Path) -> None:
    service = MemoryService(SqliteStore(tmp_path / "agent.db"))
    service.write_summary(
        scope="project",
        tags=["feedback", "pytest"],
        content="When pytest reports assert 5 == 4, inspect calculator.add",
        source_run_id="run-1",
    )

    records = service.search(tags=["feedback"], query="calculator")

    assert len(records) == 1
    assert records[0].content.startswith("When pytest reports")


def test_sensitive_memory_is_not_returned(tmp_path: Path) -> None:
    service = MemoryService(SqliteStore(tmp_path / "agent.db"))
    service.write_summary(
        scope="project",
        tags=["credential"],
        content="provider token demo-redaction-value-123456",
        source_run_id=None,
        sensitive=True,
    )

    records = service.search(tags=["credential"], query="api")

    assert records == []
```

- [x] **Step 2: Run memory tests and verify red**

Run: `pytest tests/test_memory.py -v`

Expected: FAIL with import error for `coding_agent.memory`.

- [x] **Step 3: Implement memory service**

Create `src/coding_agent/memory.py`:

```python
from __future__ import annotations

from coding_agent.domain import MemoryRecord
from coding_agent.store import SqliteStore


class MemoryService:
    def __init__(self, store: SqliteStore) -> None:
        self.store = store

    def write_summary(
        self,
        scope: str,
        tags: list[str],
        content: str,
        source_run_id: str | None,
        sensitive: bool = False,
        confidence: float = 1.0,
    ) -> str:
        return self.store.write_memory(
            scope=scope,
            kind="summary",
            tags=tags,
            content=content,
            source_run_id=source_run_id,
            confidence=confidence,
            sensitive=sensitive,
        )

    def search(self, tags: list[str], query: str) -> list[MemoryRecord]:
        return self.store.search_memory(tags=tags, query=query)
```

- [x] **Step 4: Extend ToolContext and register memory tools**

Modify `src/coding_agent/tools/base.py` so `ToolContext` accepts an optional memory service:

```python
from typing import Any

class ToolContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    workspace: Path
    policy: PolicyProfile
    memory: Any | None = None
```

Add memory handlers to `src/coding_agent/tools/dispatcher.py`:

```python
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
```

Update `build_default_dispatcher` signature to accept `memory: object | None = None`, pass it into `ToolContext`, and register `memory_search` and `memory_write`.

- [x] **Step 5: Run memory tests and full backend unit slice**

Run: `pytest tests/test_memory.py tests/test_tools.py -v`

Expected: PASS for both files.

- [x] **Step 6: Commit Task 8**

Run:

```bash
git add src/coding_agent/memory.py src/coding_agent/tools/base.py src/coding_agent/tools/dispatcher.py tests/test_memory.py
git commit -m "feat: add deterministic memory service"
```

### Task 9: Mock LLM Provider And Agent Loop Vertical Slice

**Files:**
- Create: `src/coding_agent/llm.py`
- Create: `src/coding_agent/agent_loop.py`
- Test: `tests/test_agent_loop.py`

**Interfaces:**
- Consumes: `parse_action`, `ToolDispatcher`, `MemoryService`, `SqliteStore`, `EventBus`.
- Produces: `LLMProvider`, `MockLLMProvider`, `AgentLoop.run(task: str) -> RunSummary`, `RunSummary(run_id, status, feedback)`.

- [x] **Step 1: Write failing agent loop tests**

Create `tests/test_agent_loop.py`:

```python
from pathlib import Path

from coding_agent.agent_loop import AgentLoop
from coding_agent.events import EventBus
from coding_agent.guardrails import GuardrailEngine
from coding_agent.llm import MockLLMProvider
from coding_agent.memory import MemoryService
from coding_agent.policies import load_policy
from coding_agent.store import SqliteStore
from coding_agent.tools.dispatcher import build_default_dispatcher


def _loop(tmp_path: Path, workspace: Path, script_name: str) -> AgentLoop:
    store = SqliteStore(tmp_path / "agent.db")
    policy = load_policy("strict_demo", Path("config/policies"))
    memory = MemoryService(store)
    dispatcher = build_default_dispatcher(GuardrailEngine(policy, workspace), workspace, policy, memory=memory)
    return AgentLoop(
        store=store,
        events=EventBus(store),
        memory=memory,
        dispatcher=dispatcher,
        llm=MockLLMProvider(script_name=script_name),
        workspace=workspace,
        policy_profile="strict_demo",
        llm_mode="mock",
        max_steps=8,
    )


def test_mock_loop_blocks_dangerous_action(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    loop = _loop(tmp_path, workspace, "dangerous_action")

    summary = loop.run("demonstrate guardrail")

    assert summary.status == "failed"
    assert any(item.type == "guardrail_blocked" for item in summary.feedback)


def test_mock_loop_fixes_sample_after_feedback(tmp_path: Path) -> None:
    workspace = tmp_path / "sample"
    workspace.mkdir()
    (workspace / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (workspace / "test_calculator.py").write_text(
        "from calculator import add\n\n"
        "def test_add_positive_numbers():\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )
    loop = _loop(tmp_path, workspace, "bugfix_with_feedback")

    summary = loop.run("fix calculator")

    assert summary.status == "succeeded"
    assert "return a + b" in (workspace / "calculator.py").read_text(encoding="utf-8")
```

- [x] **Step 2: Run agent loop tests and verify red**

Run: `pytest tests/test_agent_loop.py -v`

Expected: FAIL with import errors for `coding_agent.agent_loop` and `coding_agent.llm`.

- [x] **Step 3: Implement mock LLM provider**

Create `src/coding_agent/llm.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass

from coding_agent.domain import FeedbackSignal


@dataclass(frozen=True)
class LLMContext:
    task: str
    step_index: int
    feedback: list[FeedbackSignal]


class LLMProvider:
    def next_action(self, context: LLMContext) -> str:
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    def __init__(self, script_name: str) -> None:
        self.script_name = script_name

    def next_action(self, context: LLMContext) -> str:
        if self.script_name == "dangerous_action":
            return json.dumps({"kind": "tool", "tool": "read_file", "args": {"path": "../outside.txt"}, "reason": "attempt unsafe read", "expectation": "guardrail blocks it"})
        if self.script_name == "bugfix_with_feedback":
            return self._bugfix_action(context)
        raise ValueError(f"unknown mock script: {self.script_name}")

    def _bugfix_action(self, context: LLMContext) -> str:
        feedback_types = {item.type.value for item in context.feedback}
        if context.step_index == 0:
            payload = {"kind": "tool", "tool": "run_tests", "args": {"target": "."}, "reason": "observe failing tests", "expectation": "pytest failure summary"}
        elif "test_failed" in feedback_types and context.step_index == 1:
            payload = {"kind": "tool", "tool": "write_file", "args": {"path": "calculator.py", "content": "def add(a, b):\n    return a * b\n"}, "reason": "first attempted fix", "expectation": "tests may still fail"}
        elif "file_diff" in feedback_types or context.step_index == 2:
            payload = {"kind": "tool", "tool": "run_tests", "args": {"target": "."}, "reason": "check first fix", "expectation": "feedback tells whether fix worked"}
        elif "test_failed" in feedback_types:
            payload = {"kind": "tool", "tool": "write_file", "args": {"path": "calculator.py", "content": "def add(a, b):\n    return a + b\n"}, "reason": "apply correct addition fix", "expectation": "tests pass after rerun"}
        else:
            payload = {"kind": "final", "args": {}, "reason": "task complete", "expectation": "agent stops"}
        return json.dumps(payload)
```

- [x] **Step 4: Implement agent loop**

Create `src/coding_agent/agent_loop.py`:

```python
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from coding_agent.action_parser import parse_action
from coding_agent.domain import ActionKind, FeedbackSignal, FeedbackType, RunStatus
from coding_agent.events import EventBus
from coding_agent.feedback import feedback_from_tool_result
from coding_agent.llm import LLMContext, LLMProvider
from coding_agent.memory import MemoryService
from coding_agent.store import SqliteStore
from coding_agent.tools.dispatcher import ToolDispatcher


class RunSummary(BaseModel):
    run_id: str
    status: str
    feedback: list[FeedbackSignal]


class AgentLoop:
    def __init__(
        self,
        store: SqliteStore,
        events: EventBus,
        memory: MemoryService,
        dispatcher: ToolDispatcher,
        llm: LLMProvider,
        workspace: Path,
        policy_profile: str,
        llm_mode: str,
        max_steps: int,
    ) -> None:
        self.store = store
        self.events = events
        self.memory = memory
        self.dispatcher = dispatcher
        self.llm = llm
        self.workspace = workspace
        self.policy_profile = policy_profile
        self.llm_mode = llm_mode
        self.max_steps = max_steps

    def run(self, task: str) -> RunSummary:
        run_id = self.store.create_run(task, str(self.workspace), self.policy_profile, self.llm_mode)
        self.store.update_run_status(run_id, RunStatus.RUNNING)
        self.events.append_event(run_id, "run.started", {"task": task})
        feedback: list[FeedbackSignal] = []

        for step_index in range(self.max_steps):
            raw = self.llm.next_action(LLMContext(task=task, step_index=step_index, feedback=feedback))
            self.events.append_event(run_id, "llm.raw", {"step": step_index, "raw": raw})
            parsed = parse_action(raw)
            if not parsed.ok:
                assert parsed.feedback is not None
                feedback = [parsed.feedback]
                self.events.append_event(run_id, "feedback", parsed.feedback.model_dump(mode="json"))
                continue

            action = parsed.action
            assert action is not None
            if action.kind is ActionKind.FINAL:
                self.store.update_run_status(run_id, RunStatus.SUCCEEDED)
                self.events.append_event(run_id, "run.finished", {"status": "succeeded"})
                return RunSummary(run_id=run_id, status="succeeded", feedback=feedback)

            result = self.dispatcher.dispatch(action)
            self.events.append_event(run_id, "tool.result", result.model_dump(mode="json"))
            feedback = feedback_from_tool_result(result)

            if result.status == "blocked":
                self.store.update_run_status(run_id, RunStatus.FAILED)
                self.events.append_event(run_id, "run.finished", {"status": "failed"})
                return RunSummary(run_id=run_id, status="failed", feedback=feedback)

            if result.artifacts.get("diff_summary"):
                feedback = [FeedbackSignal(type=FeedbackType.FILE_DIFF, severity="info", summary=result.artifacts["diff_summary"], details=result.artifacts)]

            for item in feedback:
                self.events.append_event(run_id, "feedback", item.model_dump(mode="json"))

            if any(item.type is FeedbackType.TEST_PASSED for item in feedback):
                self.store.update_run_status(run_id, RunStatus.SUCCEEDED)
                self.events.append_event(run_id, "run.finished", {"status": "succeeded"})
                return RunSummary(run_id=run_id, status="succeeded", feedback=feedback)

        self.store.update_run_status(run_id, RunStatus.FAILED)
        self.events.append_event(run_id, "run.finished", {"status": "failed", "reason": "max_steps"})
        return RunSummary(run_id=run_id, status="failed", feedback=feedback)
```

- [x] **Step 5: Run agent loop tests and verify green**

Run: `pytest tests/test_agent_loop.py -v`

Expected: PASS with `2 passed`.

- [x] **Step 6: Commit Task 9**

Run:

```bash
git add src/coding_agent/llm.py src/coding_agent/agent_loop.py tests/test_agent_loop.py
git commit -m "feat: add mock-driven agent loop"
```

### Task 10: Typer CLI And Demo Report Export

**Files:**
- Create: `src/coding_agent/cli.py`
- Create: `src/coding_agent/__main__.py`
- Create: `scripts/export_run.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `AgentLoop`, `MockLLMProvider`, `SqliteStore`, default dispatcher.
- Produces: CLI commands `coding-agent demo dangerous-action`, `coding-agent demo bugfix`, `python -m coding_agent demo bugfix`.

- [x] **Step 1: Write failing CLI tests**

Create `tests/test_cli.py`:

```python
from typer.testing import CliRunner

from coding_agent.cli import app


def test_demo_dangerous_action_outputs_blocked_status() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["demo", "dangerous-action"])

    assert result.exit_code == 1
    assert "guardrail_blocked" in result.stdout


def test_demo_bugfix_outputs_succeeded_status() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["demo", "bugfix"])

    assert result.exit_code == 0
    assert "succeeded" in result.stdout
```

- [x] **Step 2: Run CLI tests and verify red**

Run: `pytest tests/test_cli.py -v`

Expected: FAIL with import error for `coding_agent.cli`.

- [x] **Step 3: Implement CLI entry points**

Create `src/coding_agent/cli.py`:

```python
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import typer

from coding_agent.agent_loop import AgentLoop
from coding_agent.events import EventBus
from coding_agent.guardrails import GuardrailEngine
from coding_agent.llm import MockLLMProvider
from coding_agent.memory import MemoryService
from coding_agent.policies import load_policy
from coding_agent.store import SqliteStore
from coding_agent.tools.dispatcher import build_default_dispatcher

app = typer.Typer(help="CodingAgent harness CLI")


def _copy_sample_workspace() -> Path:
    tempdir = Path(tempfile.mkdtemp(prefix="coding-agent-demo-"))
    shutil.copytree(Path("demos/sample_workspace"), tempdir / "workspace")
    return tempdir / "workspace"


def _build_loop(workspace: Path, db_path: Path, script_name: str) -> AgentLoop:
    store = SqliteStore(db_path)
    policy = load_policy("strict_demo", Path("config/policies"))
    memory = MemoryService(store)
    dispatcher = build_default_dispatcher(GuardrailEngine(policy, workspace), workspace, policy, memory=memory)
    return AgentLoop(
        store=store,
        events=EventBus(store),
        memory=memory,
        dispatcher=dispatcher,
        llm=MockLLMProvider(script_name=script_name),
        workspace=workspace,
        policy_profile="strict_demo",
        llm_mode="mock",
        max_steps=8,
    )


@app.command()
def demo(name: str = typer.Argument(..., help="dangerous-action or bugfix")) -> None:
    script_name = "dangerous_action" if name == "dangerous-action" else "bugfix_with_feedback"
    workspace = Path(tempfile.mkdtemp(prefix="coding-agent-empty-")) if name == "dangerous-action" else _copy_sample_workspace()
    loop = _build_loop(workspace, workspace.parent / "agent.db", script_name)
    summary = loop.run(f"demo {name}")
    typer.echo(json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2))
    raise typer.Exit(code=0 if summary.status == "succeeded" else 1)
```

Create `src/coding_agent/__main__.py`:

```python
from coding_agent.cli import app

app()
```

Create `scripts/export_run.py`:

```python
from __future__ import annotations

import json
import sys
from pathlib import Path

from coding_agent.store import SqliteStore


def main() -> int:
    db_path = Path(sys.argv[1])
    run_id = sys.argv[2]
    store = SqliteStore(db_path)
    print(json.dumps(store.list_events(run_id), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [x] **Step 4: Run CLI tests and verify green**

Run: `pytest tests/test_cli.py -v`

Expected: PASS with `2 passed`.

- [x] **Step 5: Manually verify CLI commands**

Run: `python -m coding_agent demo bugfix`

Expected: stdout contains JSON with `"status": "succeeded"`, and exit code is 0.

Run: `python -m coding_agent demo dangerous-action`

Expected: stdout contains `guardrail_blocked`, and exit code is 1.

- [x] **Step 6: Commit Task 10**

Run:

```bash
git add src/coding_agent/cli.py src/coding_agent/__main__.py scripts/export_run.py tests/test_cli.py
git commit -m "feat: add mock demo cli"
```

### Task 11: FastAPI API, SSE Events, And Admin Auth

**Files:**
- Create: `src/coding_agent/api.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `SqliteStore`, `EventBus`, `AgentLoop` builder pieces.
- Produces: `create_app(data_dir: Path | None = None) -> FastAPI`, routes `POST /api/runs/demo`, `GET /api/runs/{run_id}/events`, `GET /api/policies`, `GET /api/credentials/status`, `POST /api/approvals/{approval_id}/decision`.

- [x] **Step 1: Write failing API tests**

Create `tests/test_api.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from coding_agent.api import create_app


def test_create_bugfix_demo_run(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post("/api/runs/demo", json={"name": "bugfix"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["run_id"].startswith("run-")


def test_events_endpoint_returns_sse_lines(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))
    run = client.post("/api/runs/demo", json={"name": "bugfix"}).json()

    response = client.get(f"/api/runs/{run['run_id']}/events")

    assert response.status_code == 200
    assert "event: run.started" in response.text
    assert "data:" in response.text


def test_policy_endpoint_lists_profiles(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get("/api/policies")

    assert response.status_code == 200
    assert "strict_demo" in response.json()["profiles"]
```

- [x] **Step 2: Run API tests and verify red**

Run: `pytest tests/test_api.py -v`

Expected: FAIL with import error for `coding_agent.api`.

- [x] **Step 3: Implement FastAPI app**

Create `src/coding_agent/api.py`:

```python
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from coding_agent.agent_loop import AgentLoop
from coding_agent.events import EventBus
from coding_agent.guardrails import GuardrailEngine
from coding_agent.llm import MockLLMProvider
from coding_agent.memory import MemoryService
from coding_agent.policies import load_policy
from coding_agent.store import SqliteStore
from coding_agent.tools.dispatcher import build_default_dispatcher


class DemoRequest(BaseModel):
    name: str


def _workspace_for_demo(name: str) -> Path:
    if name == "dangerous-action":
        workspace = Path(tempfile.mkdtemp(prefix="coding-agent-empty-"))
        return workspace
    if name == "bugfix":
        tempdir = Path(tempfile.mkdtemp(prefix="coding-agent-demo-"))
        shutil.copytree(Path("demos/sample_workspace"), tempdir / "workspace")
        return tempdir / "workspace"
    raise HTTPException(status_code=400, detail="unknown demo")


def _run_demo(name: str, data_dir: Path) -> dict[str, Any]:
    workspace = _workspace_for_demo(name)
    store = SqliteStore(data_dir / "agent.db")
    policy = load_policy("strict_demo", Path("config/policies"))
    memory = MemoryService(store)
    dispatcher = build_default_dispatcher(GuardrailEngine(policy, workspace), workspace, policy, memory=memory)
    script_name = "dangerous_action" if name == "dangerous-action" else "bugfix_with_feedback"
    loop = AgentLoop(
        store=store,
        events=EventBus(store),
        memory=memory,
        dispatcher=dispatcher,
        llm=MockLLMProvider(script_name=script_name),
        workspace=workspace,
        policy_profile="strict_demo",
        llm_mode="mock",
        max_steps=8,
    )
    return loop.run(f"demo {name}").model_dump(mode="json")


def create_app(data_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="CodingAgent Harness")
    runtime_dir = data_dir or Path(os.environ.get("CODING_AGENT_DATA_DIR", ".coding-agent-data"))
    runtime_dir.mkdir(parents=True, exist_ok=True)

    @app.post("/api/runs/demo")
    def create_demo_run(request: DemoRequest) -> dict[str, Any]:
        return _run_demo(request.name, runtime_dir)

    @app.get("/api/runs/{run_id}/events")
    def run_events(run_id: str) -> StreamingResponse:
        store = SqliteStore(runtime_dir / "agent.db")
        events = store.list_events(run_id)

        def stream() -> Any:
            for event in events:
                yield f"event: {event['event_type']}\n"
                yield f"data: {json.dumps(event['payload'], ensure_ascii=False)}\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/api/policies")
    def policies() -> dict[str, list[str]]:
        return {"profiles": ["strict_demo", "balanced_dev"]}

    @app.get("/api/credentials/status")
    def credential_status() -> dict[str, object]:
        configured = bool(os.environ.get("OPENAI_API_KEY"))
        real_enabled = os.environ.get("ENABLE_REAL_LLM", "false").lower() == "true"
        return {"provider": "openai-compatible", "configured": configured, "real_enabled": real_enabled}

    @app.post("/api/approvals/{approval_id}/decision")
    def approval_decision(approval_id: str) -> dict[str, str]:
        return {"approval_id": approval_id, "state": "recorded"}

    return app


app = create_app()
```

- [x] **Step 4: Run API tests and verify green**

Run: `pytest tests/test_api.py -v`

Expected: PASS with `3 passed`.

- [x] **Step 5: Commit Task 11**

Run:

```bash
git add src/coding_agent/api.py tests/test_api.py
git commit -m "feat: expose harness api and sse"
```

### Task 12: Frontend Scaffold, Types, And API Client

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/api.test.ts`

**Interfaces:**
- Consumes: FastAPI routes from Task 11.
- Produces: `createDemoRun(name)`, `fetchPolicies()`, `fetchCredentialStatus()`, `openRunEventSource(runId)` and TypeScript types `RunSummary`, `PolicyList`, `CredentialStatus`.

- [x] **Step 1: Write failing API client tests**

Create `frontend/src/api.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";
import { createDemoRun, fetchPolicies } from "./api";

describe("api client", () => {
  it("creates a bugfix demo run", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ run_id: "run-1", status: "succeeded", feedback: [] }) });
    vi.stubGlobal("fetch", fetchMock);

    const run = await createDemoRun("bugfix");

    expect(run.status).toBe("succeeded");
    expect(fetchMock).toHaveBeenCalledWith("/api/runs/demo", expect.objectContaining({ method: "POST" }));
  });

  it("fetches policy profiles", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ profiles: ["strict_demo"] }) }));

    const policies = await fetchPolicies();

    expect(policies.profiles).toContain("strict_demo");
  });
});
```

- [x] **Step 2: Run frontend tests and verify red**

Run: `cd frontend && npm install && npm run test -- --run`

Expected: FAIL because `package.json` and `src/api.ts` do not exist.

- [x] **Step 3: Add frontend package and Vite config**

Create `frontend/package.json`:

```json
{
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "tsc -b && vite build",
    "test": "vitest"
  },
  "dependencies": {
    "@vitejs/plugin-react": "latest",
    "vite": "latest",
    "typescript": "latest",
    "react": "latest",
    "react-dom": "latest",
    "lucide-react": "latest"
  },
  "devDependencies": {
    "vitest": "latest",
    "jsdom": "latest",
    "@testing-library/react": "latest",
    "@testing-library/jest-dom": "latest"
  }
}
```

Create `frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CodingAgent</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `frontend/vite.config.ts`:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom" },
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
});
```

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2022"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"]
}
```

- [x] **Step 4: Implement frontend types and API client**

Create `frontend/src/types.ts`:

```ts
export type FeedbackSignal = {
  type: string;
  severity: "info" | "warning" | "error";
  summary: string;
  details: Record<string, unknown>;
};

export type RunSummary = {
  run_id: string;
  status: string;
  feedback: FeedbackSignal[];
};

export type PolicyList = { profiles: string[] };
export type CredentialStatus = { provider: string; configured: boolean; real_enabled: boolean };
```

Create `frontend/src/api.ts`:

```ts
import type { CredentialStatus, PolicyList, RunSummary } from "./types";

async function jsonRequest<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export function createDemoRun(name: "bugfix" | "dangerous-action"): Promise<RunSummary> {
  return jsonRequest<RunSummary>("/api/runs/demo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export function fetchPolicies(): Promise<PolicyList> {
  return jsonRequest<PolicyList>("/api/policies");
}

export function fetchCredentialStatus(): Promise<CredentialStatus> {
  return jsonRequest<CredentialStatus>("/api/credentials/status");
}

export function openRunEventSource(runId: string): EventSource {
  return new EventSource(`/api/runs/${runId}/events`);
}
```

- [x] **Step 5: Run frontend API tests and verify green**

Run: `cd frontend && npm run test -- --run src/api.test.ts`

Expected: PASS with `2 passed`.

- [x] **Step 6: Commit Task 12**

Run:

```bash
git add frontend/package.json frontend/index.html frontend/vite.config.ts frontend/tsconfig.json frontend/src/types.ts frontend/src/api.ts frontend/src/api.test.ts
git commit -m "feat: scaffold frontend api client"
```

### Task 13: Frontend Dashboard, Demo Center, Run Detail, And Admin Views

**Files:**
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: `createDemoRun`, `fetchPolicies`, `fetchCredentialStatus`, `openRunEventSource`.
- Produces: operational dashboard with Demo Center, Run Detail, Approval Queue placeholder driven by API data, Memory, Policies, Credentials, Settings tabs.

- [x] **Step 1: Write failing App tests**

Create `frontend/src/App.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./api", () => ({
  createDemoRun: vi.fn().mockResolvedValue({ run_id: "run-1", status: "succeeded", feedback: [] }),
  fetchPolicies: vi.fn().mockResolvedValue({ profiles: ["strict_demo", "balanced_dev"] }),
  fetchCredentialStatus: vi.fn().mockResolvedValue({ provider: "openai-compatible", configured: false, real_enabled: false }),
  openRunEventSource: vi.fn(() => ({ close: vi.fn(), addEventListener: vi.fn() })),
}));

describe("App", () => {
  it("renders dashboard and demo controls", async () => {
    render(<App />);

    expect(await screen.findByText("CodingAgent"));
    expect(screen.getByRole("button", { name: /Run bugfix demo/i })).toBeInTheDocument();
  });

  it("starts a demo from the dashboard", async () => {
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: /Run bugfix demo/i }));

    expect(await screen.findByText(/run-1/)).toBeInTheDocument();
  });
});
```

- [x] **Step 2: Run App tests and verify red**

Run: `cd frontend && npm run test -- --run src/App.test.tsx`

Expected: FAIL because `App.tsx` and `main.tsx` do not exist.

- [x] **Step 3: Implement React entry and App**

Create `frontend/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

Create `frontend/src/App.tsx`:

```tsx
import { CheckCircle2, KeyRound, ListChecks, Play, Shield, SquareActivity } from "lucide-react";
import { useEffect, useState } from "react";
import { createDemoRun, fetchCredentialStatus, fetchPolicies } from "./api";
import type { CredentialStatus, PolicyList, RunSummary } from "./types";

type Tab = "dashboard" | "run" | "approvals" | "memory" | "policies" | "credentials" | "settings";

export default function App() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [run, setRun] = useState<RunSummary | null>(null);
  const [policies, setPolicies] = useState<PolicyList>({ profiles: [] });
  const [credentials, setCredentials] = useState<CredentialStatus | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchPolicies().then(setPolicies);
    fetchCredentialStatus().then(setCredentials);
  }, []);

  async function startDemo(name: "bugfix" | "dangerous-action") {
    setBusy(true);
    try {
      const nextRun = await createDemoRun(name);
      setRun(nextRun);
      setTab("run");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand"><Shield size={22} /> CodingAgent</div>
        <button onClick={() => setTab("dashboard")}>Dashboard</button>
        <button onClick={() => setTab("run")}>Run Detail</button>
        <button onClick={() => setTab("approvals")}>Approval Queue</button>
        <button onClick={() => setTab("memory")}>Memory</button>
        <button onClick={() => setTab("policies")}>Policies</button>
        <button onClick={() => setTab("credentials")}>Credentials</button>
        <button onClick={() => setTab("settings")}>Settings</button>
      </aside>
      <section className="content">
        {tab === "dashboard" && (
          <div className="panel-grid">
            <section className="panel hero-panel">
              <h1>CodingAgent</h1>
              <p>Mock-first coding agent harness with deterministic guardrails, feedback, memory, and tool dispatch.</p>
              <div className="actions">
                <button disabled={busy} onClick={() => startDemo("bugfix")}><Play size={16} /> Run bugfix demo</button>
                <button disabled={busy} onClick={() => startDemo("dangerous-action")}><Shield size={16} /> Run guardrail demo</button>
              </div>
            </section>
            <section className="panel"><SquareActivity /> <strong>Policy</strong><span>{policies.profiles.join(", ") || "loading"}</span></section>
            <section className="panel"><KeyRound /> <strong>Real LLM</strong><span>{credentials?.configured ? "configured" : "mock only"}</span></section>
            <section className="panel"><ListChecks /> <strong>Approvals</strong><span>Queue ready for HITL decisions</span></section>
          </div>
        )}
        {tab === "run" && <section className="panel"><h2>Run Detail</h2>{run ? <pre>{JSON.stringify(run, null, 2)}</pre> : <p>No run selected</p>}</section>}
        {tab === "approvals" && <section className="panel"><h2>Approval Queue</h2><p>Dangerous actions that need HITL review appear here.</p></section>}
        {tab === "memory" && <section className="panel"><h2>Memory</h2><p>Event and summary memories will be searchable by tag and keyword.</p></section>}
        {tab === "policies" && <section className="panel"><h2>Policies</h2><pre>{JSON.stringify(policies, null, 2)}</pre></section>}
        {tab === "credentials" && <section className="panel"><h2>Credentials</h2><pre>{JSON.stringify(credentials, null, 2)}</pre></section>}
        {tab === "settings" && <section className="panel"><h2>Settings</h2><p>Mock mode is the public deployment default.</p><CheckCircle2 /></section>}
      </section>
    </main>
  );
}
```

Create `frontend/src/styles.css` with stable dashboard sizing and non-marketing layout:

```css
* { box-sizing: border-box; }
body { margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #18202f; background: #eef2f7; }
button { border: 1px solid #c8d0dd; border-radius: 6px; background: #ffffff; color: #18202f; min-height: 36px; padding: 0 12px; display: inline-flex; align-items: center; gap: 8px; cursor: pointer; }
button:hover { border-color: #59708f; }
button:disabled { opacity: 0.55; cursor: progress; }
.shell { min-height: 100vh; display: grid; grid-template-columns: 248px minmax(0, 1fr); }
.sidebar { background: #172033; color: #f8fafc; padding: 18px; display: flex; flex-direction: column; gap: 8px; }
.sidebar button { justify-content: flex-start; background: transparent; color: #f8fafc; border-color: rgba(255,255,255,0.15); }
.brand { display: flex; align-items: center; gap: 10px; font-weight: 700; margin-bottom: 18px; }
.content { padding: 24px; min-width: 0; }
.panel-grid { display: grid; grid-template-columns: repeat(3, minmax(180px, 1fr)); gap: 16px; }
.panel { background: #ffffff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; min-width: 0; box-shadow: 0 1px 2px rgba(22, 32, 51, 0.04); }
.hero-panel { grid-column: 1 / -1; min-height: 220px; display: flex; flex-direction: column; justify-content: center; }
h1 { font-size: 36px; line-height: 1.1; margin: 0 0 10px; letter-spacing: 0; }
h2 { font-size: 22px; margin: 0 0 12px; letter-spacing: 0; }
p { max-width: 760px; line-height: 1.55; }
.actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }
pre { overflow: auto; background: #101827; color: #eef2f7; padding: 14px; border-radius: 6px; }
@media (max-width: 760px) { .shell { grid-template-columns: 1fr; } .sidebar { position: static; } .panel-grid { grid-template-columns: 1fr; } }
```

- [x] **Step 4: Run App tests and frontend build**

Run: `cd frontend && npm run test -- --run src/App.test.tsx`

Expected: PASS with `2 passed`.

Run: `cd frontend && npm run build`

Expected: PASS and creates `frontend/dist`.

- [x] **Step 5: Commit Task 13**

Run:

```bash
git add frontend/src/main.tsx frontend/src/App.tsx frontend/src/styles.css frontend/src/App.test.tsx
git commit -m "feat: add operational web dashboard"
```

### Task 14: Credential Status And Optional Real LLM Provider

**Files:**
- Modify: `src/coding_agent/llm.py`
- Create: `src/coding_agent/credentials.py`
- Modify: `src/coding_agent/api.py`
- Modify: `src/coding_agent/cli.py`
- Test: `tests/test_credentials_llm.py`

**Interfaces:**
- Consumes: environment variables `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, `ENABLE_REAL_LLM`.
- Produces: `CredentialService.status()`, `RealLLMProvider.next_action(context)`, CLI `coding-agent credentials status`.

- [x] **Step 1: Write failing credential and real provider tests**

Create `tests/test_credentials_llm.py`:

```python
import os

from coding_agent.credentials import CredentialService
from coding_agent.llm import LLMContext, RealLLMProvider


def test_credential_status_without_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ENABLE_REAL_LLM", "false")

    status = CredentialService.from_env().status()

    assert status["configured"] is False
    assert status["real_enabled"] is False


def test_real_provider_refuses_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "demo-token-value-not-real")
    monkeypatch.setenv("ENABLE_REAL_LLM", "false")
    provider = RealLLMProvider.from_env()

    try:
        provider.next_action(LLMContext(task="x", step_index=0, feedback=[]))
    except RuntimeError as exc:
        assert "ENABLE_REAL_LLM" in str(exc)
    else:
        raise AssertionError("provider should refuse when disabled")
```

- [x] **Step 2: Run credential tests and verify red**

Run: `pytest tests/test_credentials_llm.py -v`

Expected: FAIL with import error for `coding_agent.credentials` and `RealLLMProvider`.

- [x] **Step 3: Implement credential status service**

Create `src/coding_agent/credentials.py`:

```python
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CredentialService:
    provider_token: str | None
    base_url: str
    model: str
    real_enabled: bool

    @classmethod
    def from_env(cls) -> "CredentialService":
        return cls(
            provider_token=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL", "https://njusehub.info/v1"),
            model=os.environ.get("OPENAI_MODEL", "glm-5.2"),
            real_enabled=os.environ.get("ENABLE_REAL_LLM", "false").lower() == "true",
        )

    def status(self) -> dict[str, object]:
        return {
            "provider": "openai-compatible",
            "configured": bool(self.provider_token),
            "source": "environment" if self.provider_token else "missing",
            "base_url": self.base_url,
            "model": self.model,
            "real_enabled": self.real_enabled,
        }
```

- [x] **Step 4: Implement real LLM provider gate**

Add to `src/coding_agent/llm.py`:

```python
import os
import httpx


class RealLLMProvider(LLMProvider):
    def __init__(self, provider_token: str | None, base_url: str, model: str, enabled: bool) -> None:
        self.provider_token = provider_token
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.enabled = enabled

    @classmethod
    def from_env(cls) -> "RealLLMProvider":
        return cls(
            provider_token=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL", "https://njusehub.info/v1"),
            model=os.environ.get("OPENAI_MODEL", "glm-5.2"),
            enabled=os.environ.get("ENABLE_REAL_LLM", "false").lower() == "true",
        )

    def next_action(self, context: LLMContext) -> str:
        if not self.enabled:
            raise RuntimeError("Real LLM is disabled; set ENABLE_REAL_LLM=true to enable it")
        if not self.provider_token:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.provider_token}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Return exactly one strict JSON CodingAgent action."},
                    {"role": "user", "content": f"Task: {context.task}\nStep: {context.step_index}"},
                ],
                "temperature": 0,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload["choices"][0]["message"]["content"])
```

- [x] **Step 5: Wire credential status into API and CLI**

Modify `/api/credentials/status` in `src/coding_agent/api.py` to use `CredentialService.from_env().status()`.

Add a CLI command to `src/coding_agent/cli.py`:

```python
from coding_agent.credentials import CredentialService


@app.command("credentials-status")
def credentials_status() -> None:
    typer.echo(json.dumps(CredentialService.from_env().status(), ensure_ascii=False, indent=2))
```

- [x] **Step 6: Run credential tests and verify green**

Run: `pytest tests/test_credentials_llm.py tests/test_api.py -v`

Expected: PASS for both files.

- [x] **Step 7: Commit Task 14**

Run:

```bash
git add src/coding_agent/credentials.py src/coding_agent/llm.py src/coding_agent/api.py src/coding_agent/cli.py tests/test_credentials_llm.py
git commit -m "feat: gate optional real llm credentials"
```

### Task 15: Docker, CI, Git Ignore, And Deployment Documentation

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.gitlab-ci.yml`
- Create: `.github/workflows/ci.yml`
- Modify: `README.md`
- Test: no unit test file; verification commands are Docker, backend tests, frontend build, CI syntax review.

**Interfaces:**
- Produces: local Docker Compose service exposing WebUI/API on port 8000, GitLab `unit-test` job, GitHub Actions CI.

- [x] **Step 1: Write distribution files**

Create `.gitignore`:

```gitignore
__pycache__/
.pytest_cache/
.ruff_cache/
.venv/
node_modules/
frontend/dist/
.coding-agent-data/
*.db
*.sqlite
.env
.env.*
!.env.example
run-exports/
```

Create `.env.example`:

```env
LLM_MODE=mock
ENABLE_REAL_LLM=false
OPENAI_BASE_URL=https://njusehub.info/v1
OPENAI_MODEL=glm-5.2
OPENAI_API_KEY=
ADMIN_PASSWORD=change-this-before-deploying
CODING_AGENT_DATA_DIR=/data
```

Create `Dockerfile`:

```dockerfile
FROM node:22-bookworm AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json ./package.json
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY pyproject.toml ./
COPY src ./src
COPY config ./config
COPY demos ./demos
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["uvicorn", "coding_agent.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `docker-compose.yml`:

```yaml
services:
  coding-agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      LLM_MODE: ${LLM_MODE:-mock}
      ENABLE_REAL_LLM: ${ENABLE_REAL_LLM:-false}
      OPENAI_BASE_URL: ${OPENAI_BASE_URL:-https://njusehub.info/v1}
      OPENAI_MODEL: ${OPENAI_MODEL:-glm-5.2}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD:?set ADMIN_PASSWORD in .env}
      CODING_AGENT_DATA_DIR: /data
    volumes:
      - coding-agent-data:/data
volumes:
  coding-agent-data:
```

- [x] **Step 2: Add CI files**

Create `.gitlab-ci.yml`:

```yaml
stages:
  - test

unit-test:
  stage: test
  image: python:3.12
  script:
    - pip install -e .[dev]
    - pytest -q
```

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e .[dev]
      - run: pytest -q

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
      - run: npm install
        working-directory: frontend
      - run: npm run build
        working-directory: frontend

  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t coding-agent:ci .
```

- [x] **Step 3: Update README deployment and demo sections**

Modify `README.md` to include these commands exactly:

```bash
python -m coding_agent demo bugfix
python -m coding_agent demo dangerous-action
uvicorn coding_agent.api:app --reload
cp .env.example .env
docker compose up --build
```

Add Aliyun Ubuntu notes: open the chosen security group port, keep `.env` only on the server, set a non-default `ADMIN_PASSWORD`, leave `ENABLE_REAL_LLM=false` for public demos, and check logs with `docker compose logs -f coding-agent`.

- [x] **Step 4: Run distribution verification**

Run: `pytest -q`

Expected: all backend tests pass.

Run: `cd frontend && npm run build`

Expected: frontend build succeeds.

Run: `docker compose build`

Expected: Docker image builds without copying `.env` or local databases.

- [x] **Step 5: Commit Task 15**

Run:

```bash
git add .gitignore .env.example Dockerfile docker-compose.yml .gitlab-ci.yml .github/workflows/ci.yml README.md
git commit -m "chore: add docker ci and deployment docs"
```

### Task 16: Final Mechanism Verification And Course Evidence Update

**Files:**
- Modify: `SPEC_PROCESS.md`
- Modify: `AGENT_LOG.md`
- Modify: `REFLECTION.md`
- Create: `run-exports/.gitkeep` only if an empty ignored export directory is needed for local workflow; do not commit generated run JSON.

**Interfaces:**
- Produces: final recorded evidence that mock demos, tests, Docker, CI, and WebUI URL were verified.

- [x] **Step 1: Run all final verification commands**

Run: `pytest -q`

Expected: all backend tests pass.

Run: `cd frontend && npm run test -- --run`

Expected: all frontend tests pass.

Run: `cd frontend && npm run build`

Expected: frontend build passes.

Run: `python -m coding_agent demo bugfix`

Expected: exit code 0 and output status `succeeded`.

Run: `python -m coding_agent demo dangerous-action`

Expected: exit code 1 and output contains `guardrail_blocked`.

Run: `docker compose build`

Expected: image builds.

- [x] **Step 2: Record evidence in process documents**

Update `SPEC_PROCESS.md` with exact command names, dates, and observed outcomes. Update `AGENT_LOG.md` with key commits and any human intervention. Update `REFLECTION.md` with implementation-stage observations without claiming final reflection is complete.

- [x] **Step 3: Commit final evidence docs**

Run:

```bash
git add SPEC_PROCESS.md AGENT_LOG.md REFLECTION.md
git commit -m "docs: record final verification evidence"
```

---

## Cold-Start Validation Gate

Before executing Task 1, run a cold-start validation in a fresh session with a different type of agent. Give it only `SPEC.md` and `PLAN.md`, ask it to implement one small task such as Task 2 or Task 4, and require it to stop when unclear. Record misunderstandings in `SPEC_PROCESS.md`, then revise `SPEC.md` and this plan before implementation.

## Plan Self-Review

Spec coverage:

- Agent loop: Task 9.
- Mock and real LLM abstraction: Tasks 9 and 14.
- Strict Action Protocol: Task 2.
- Tool dispatch: Tasks 5, 7, and 8.
- Governance guardrails and HITL approval: Task 4, with API surface in Task 11 and WebUI surface in Task 13.
- Feedback loop: Tasks 6, 7, and 9.
- Memory: Task 8.
- WebUI one-click demo: Tasks 12 and 13.
- Docker and Aliyun deployment: Task 15.
- GitLab and GitHub CI: Task 15.
- Course evidence documents: Task 16.

Placeholder scan:

- This plan intentionally avoids unfinished markers and unspecified implementation hooks.
- Each task names exact files, interfaces, commands, and expected results.

Type consistency:

- `Action`, `ToolResult`, `FeedbackSignal`, and policy names come from Task 1 and Task 2.
- `build_default_dispatcher` gains the optional `memory` argument in Task 8; later tasks call that expanded signature.
- `RunSummary` fields use `run_id`, `status`, and `feedback`, matching frontend `RunSummary` in Task 12.
