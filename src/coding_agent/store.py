from __future__ import annotations

import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from coding_agent.domain import ApprovalRequest, ApprovalState, MemoryRecord, RunStatus, ToolResult
from coding_agent.redaction import redact_value


class SqliteStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.provider_token = os.environ.get("OPENAI_API_KEY")
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
                    sequence integer primary key autoincrement,
                    id text not null unique,
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
                create table if not exists approvals (
                    id text primary key,
                    run_id text not null,
                    action_id text not null,
                    action_json text not null,
                    state text not null,
                    rules_json text not null,
                    reason text not null,
                    step_index integer not null,
                    feedback_json text not null,
                    reviewer text,
                    reviewer_reason text,
                    execution_result_json text,
                    created_at text default current_timestamp,
                    decided_at text,
                    executed_at text
                );
                """
            )
            columns = {row["name"] for row in conn.execute("pragma table_info(events)")}
            if "sequence" not in columns:
                conn.executescript(
                    """
                    alter table events rename to events_legacy;
                    create table events (
                        sequence integer primary key autoincrement,
                        id text not null unique,
                        run_id text not null,
                        event_type text not null,
                        payload_json text not null,
                        created_at text default current_timestamp
                    );
                    insert into events(id, run_id, event_type, payload_json, created_at)
                    select id, run_id, event_type, payload_json, created_at
                    from events_legacy order by created_at, rowid;
                    drop table events_legacy;
                    """
                )

    def create_run(self, task: str, workspace: str, policy_profile: str, llm_mode: str) -> str:
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        with self._connect() as conn:
            conn.execute(
                (
                    "insert into runs(id, task, workspace, policy_profile, llm_mode, status) "
                    "values (?, ?, ?, ?, ?, ?)"
                ),
                (run_id, task, workspace, policy_profile, llm_mode, RunStatus.CREATED.value),
            )
        return run_id

    def update_run_status(self, run_id: str, status: RunStatus) -> None:
        with self._connect() as conn:
            conn.execute("update runs set status = ? where id = ?", (status.value, run_id))

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("select * from runs where id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return dict(row)

    def create_approval(self, request: ApprovalRequest) -> None:
        with self._connect() as conn:
            conn.execute(
                (
                    "insert into approvals(id, run_id, action_id, action_json, state, rules_json, "
                    "reason, step_index, feedback_json) values (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                ),
                (
                    request.id,
                    request.run_id,
                    request.action_id,
                    request.action.model_dump_json(),
                    request.state.value,
                    json.dumps(request.rules, ensure_ascii=False),
                    request.reason,
                    request.step_index,
                    json.dumps(
                        [item.model_dump(mode="json") for item in request.feedback],
                        ensure_ascii=False,
                    ),
                ),
            )

    def get_approval(self, approval_id: str) -> ApprovalRequest:
        with self._connect() as conn:
            row = conn.execute("select * from approvals where id = ?", (approval_id,)).fetchone()
        if row is None:
            raise KeyError(approval_id)
        return self._approval_from_row(row)

    def list_approvals(self, state: ApprovalState | None = None) -> list[ApprovalRequest]:
        query = "select * from approvals"
        params: tuple[str, ...] = ()
        if state is not None:
            query += " where state = ?"
            params = (state.value,)
        query += " order by created_at, id"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._approval_from_row(row) for row in rows]

    def transition_approval(
        self,
        approval_id: str,
        state: ApprovalState,
        reviewer: str,
        reason: str,
    ) -> ApprovalRequest:
        with self._connect() as conn:
            cursor = conn.execute(
                (
                    "update approvals set state = ?, reviewer = ?, reviewer_reason = ?, "
                    "decided_at = current_timestamp where id = ? and state = ?"
                ),
                (state.value, reviewer, reason, approval_id, ApprovalState.PENDING.value),
            )
            if cursor.rowcount != 1:
                exists = conn.execute(
                    "select state from approvals where id = ?", (approval_id,)
                ).fetchone()
                if exists is None:
                    raise KeyError(approval_id)
                raise ValueError(
                    f"approval must be pending; current state is {exists['state']}"
                )
        return self.get_approval(approval_id)

    def record_approval_execution(
        self, approval_id: str, result: ToolResult
    ) -> ApprovalRequest:
        with self._connect() as conn:
            cursor = conn.execute(
                (
                    "update approvals set execution_result_json = ?, executed_at = current_timestamp "
                    "where id = ? and state = ? and execution_result_json is null"
                ),
                (result.model_dump_json(), approval_id, ApprovalState.APPROVED_ONCE.value),
            )
            if cursor.rowcount != 1:
                raise ValueError("approved action has already been executed or is not approved")
        return self.get_approval(approval_id)

    @staticmethod
    def _approval_from_row(row: sqlite3.Row) -> ApprovalRequest:
        return ApprovalRequest.model_validate(
            {
                "id": row["id"],
                "run_id": row["run_id"],
                "action_id": row["action_id"],
                "action": json.loads(row["action_json"]),
                "state": row["state"],
                "rules": json.loads(row["rules_json"]),
                "reason": row["reason"],
                "step_index": row["step_index"],
                "feedback": json.loads(row["feedback_json"]),
                "reviewer": row["reviewer"],
                "reviewer_reason": row["reviewer_reason"],
                "execution_result": (
                    json.loads(row["execution_result_json"])
                    if row["execution_result_json"]
                    else None
                ),
            }
        )

    def append_event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> None:
        redacted, _ = redact_value(payload, self.provider_token)
        with self._connect() as conn:
            conn.execute(
                "insert into events(id, run_id, event_type, payload_json) values (?, ?, ?, ?)",
                (
                    f"event-{uuid.uuid4().hex[:12]}",
                    run_id,
                    event_type,
                    json.dumps(redacted, ensure_ascii=False),
                ),
            )

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                (
                    "select sequence, id, event_type, payload_json, created_at from events "
                    "where run_id = ? order by sequence"
                ),
                (run_id,),
            ).fetchall()
        return [
            {
                "sequence": row["sequence"],
                "id": row["id"],
                "event_type": row["event_type"],
                "payload": redact_value(
                    json.loads(row["payload_json"]), self.provider_token
                )[0],
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
        redacted_content = redact_value(content, self.provider_token)[0]
        with self._connect() as conn:
            conn.execute(
                (
                    "insert into memory("
                    "id, scope, kind, tags_json, content, source_run_id, confidence, sensitive"
                    ") values (?, ?, ?, ?, ?, ?, ?, ?)"
                ),
                (
                    memory_id,
                    scope,
                    kind,
                    json.dumps(tags),
                    redacted_content,
                    source_run_id,
                    confidence,
                    int(sensitive),
                ),
            )
        return memory_id

    def search_memory(
        self,
        tags: list[str],
        query: str,
        scope: str | None = None,
        limit: int | None = None,
    ) -> list[MemoryRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                (
                    "select * from memory where sensitive = 0 "
                    "order by confidence desc, created_at desc, id"
                )
            ).fetchall()
        lowered = query.lower()
        result: list[MemoryRecord] = []
        for row in rows:
            row_tags = json.loads(row["tags_json"])
            scope_match = scope is None or row["scope"] == scope
            tag_match = not tags or any(tag in row_tags for tag in tags)
            query_match = not query or lowered in row["content"].lower()
            if scope_match and tag_match and query_match:
                result.append(
                    MemoryRecord(
                        id=row["id"],
                        scope=row["scope"],
                        kind=row["kind"],
                        tags=row_tags,
                        content=redact_value(row["content"], self.provider_token)[0],
                        source_run_id=row["source_run_id"],
                        confidence=float(row["confidence"]),
                        sensitive=bool(row["sensitive"]),
                    )
                )
                if limit is not None and len(result) >= limit:
                    break
        return result
