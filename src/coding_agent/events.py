from __future__ import annotations

from enum import StrEnum
from typing import Any

from coding_agent.store import SqliteStore


class EventType(StrEnum):
    RUN_CREATED = "run.created"
    RUN_STARTED = "run.started"
    LLM_OUTPUT = "llm.output"
    GUARDRAIL_CHECKED = "guardrail.checked"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_APPROVED = "approval.approved"
    APPROVAL_REJECTED = "approval.rejected"
    TOOL_RESULT = "tool.result"
    MEMORY_WRITTEN = "memory.written"
    FEEDBACK_RECORDED = "feedback.recorded"
    RUN_FINISHED = "run.finished"


class EventBus:
    def __init__(self, store: SqliteStore) -> None:
        self.store = store

    def append_event(
        self, run_id: str, event_type: EventType | str, payload: dict[str, Any]
    ) -> None:
        self.store.append_event(run_id, EventType(event_type).value, payload)

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        return self.store.list_events(run_id)

    def list_events_after(
        self, run_id: str, after_sequence: int = 0, limit: int | None = 100
    ) -> list[dict[str, Any]]:
        return self.store.list_events_after(run_id, after_sequence, limit)
