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


def test_events_have_monotonic_persisted_sequence(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "agent.db")
    run_id = store.create_run("task", str(tmp_path), "strict_demo", "mock")

    store.append_event(run_id, "run.started", {"ordinal": 1})
    store.append_event(run_id, "feedback.recorded", {"ordinal": 2})
    store.append_event(run_id, "run.finished", {"ordinal": 3})

    events = store.list_events(run_id)
    assert [event["sequence"] for event in events] == [1, 2, 3]
    assert [event["payload"]["ordinal"] for event in events] == [1, 2, 3]


def test_structured_event_and_memory_values_are_redacted_at_persistence(
    tmp_path: Path, monkeypatch
) -> None:
    exact_token = "exact-provider-token-for-redaction-test"
    monkeypatch.setenv("OPENAI_API_KEY", exact_token)
    store = SqliteStore(tmp_path / "agent.db")
    run_id = store.create_run("task", str(tmp_path), "strict_demo", "mock")

    store.append_event(
        run_id,
        "llm.output",
        {
            "nested": {"authorization": f"Bearer {exact_token}"},
            "raw": f"provider returned {exact_token} and sk-testknownformat1234567890",
        },
    )
    store.write_memory(
        scope="project",
        kind="summary",
        tags=["provider"],
        content=f"never persist {exact_token}",
        source_run_id=run_id,
        confidence=1.0,
        sensitive=False,
    )

    serialized = str(store.list_events(run_id)) + str(store.search_memory([], ""))
    assert exact_token not in serialized
    assert "sk-testknownformat1234567890" not in serialized
    assert "provider_token:redacted" in serialized
