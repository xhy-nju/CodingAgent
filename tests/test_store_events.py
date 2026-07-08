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
