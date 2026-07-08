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

    def append_event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "insert into events(id, run_id, event_type, payload_json) values (?, ?, ?, ?)",
                (
                    f"event-{uuid.uuid4().hex[:12]}",
                    run_id,
                    event_type,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                (
                    "select id, event_type, payload_json, created_at from events "
                    "where run_id = ? order by created_at, id"
                ),
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
                    content,
                    source_run_id,
                    confidence,
                    int(sensitive),
                ),
            )
        return memory_id

    def search_memory(self, tags: list[str], query: str) -> list[MemoryRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "select * from memory where sensitive = 0 order by created_at desc"
            ).fetchall()
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
