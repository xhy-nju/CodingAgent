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
