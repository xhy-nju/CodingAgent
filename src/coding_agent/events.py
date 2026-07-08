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
