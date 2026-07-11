import sqlite3
from pathlib import Path

from keyring.errors import PasswordDeleteError

from coding_agent.credentials import CredentialService
from coding_agent.domain import RunStatus
from coding_agent.events import EventBus
from coding_agent.store import SqliteStore


class FakeKeyring:
    def __init__(self, token: str) -> None:
        self.token = token

    def get_password(self, service: str, username: str) -> str | None:
        return self.token

    def set_password(self, service: str, username: str, token: str) -> None:
        self.token = token

    def delete_password(self, service: str, username: str) -> None:
        if not self.token:
            raise PasswordDeleteError("credential not found")
        self.token = ""


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


def test_default_store_does_not_resolve_credentials(tmp_path: Path, monkeypatch) -> None:
    def fail_if_resolved(self) -> object:
        raise AssertionError("default store must not resolve credentials")

    monkeypatch.setattr(CredentialService, "resolve", fail_if_resolved)

    store = SqliteStore(tmp_path / "agent.db")

    assert store.provider_token is None


def test_events_have_monotonic_persisted_sequence(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "agent.db")
    run_id = store.create_run("task", str(tmp_path), "strict_demo", "mock")

    store.append_event(run_id, "run.started", {"ordinal": 1})
    store.append_event(run_id, "feedback.recorded", {"ordinal": 2})
    store.append_event(run_id, "run.finished", {"ordinal": 3})

    events = store.list_events(run_id)
    assert [event["sequence"] for event in events] == [1, 2, 3]
    assert [event["payload"]["ordinal"] for event in events] == [1, 2, 3]


def test_list_events_after_uses_persisted_sequence_cursor(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "agent.db")
    run_id = store.create_run("task", str(tmp_path), "strict_demo", "mock")
    store.append_event(run_id, "run.started", {"ordinal": 1})
    first = store.list_events_after(run_id, after_sequence=0)
    store.append_event(run_id, "run.finished", {"ordinal": 2})

    second = store.list_events_after(
        run_id, after_sequence=first[-1]["sequence"]
    )

    assert [event["payload"]["ordinal"] for event in second] == [2]


def test_fail_interrupted_runs_preserves_waiting_approval(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "agent.db")
    running = store.create_run("one", str(tmp_path), "strict_demo", "real")
    waiting = store.create_run("two", str(tmp_path), "strict_demo", "real")
    store.update_run_status(running, RunStatus.RUNNING)
    store.update_run_status(waiting, RunStatus.WAITING_APPROVAL)

    changed = store.fail_interrupted_runs()

    assert changed == [running]
    assert store.get_run(running)["status"] == "failed"
    assert store.get_run(running)["finished_at"] is not None
    assert store.get_run(waiting)["status"] == "waiting_approval"
    assert store.list_events(running)[-1]["payload"]["reason"] == "process_restarted"


def test_terminal_status_sets_finished_timestamp(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "agent.db")
    run_id = store.create_run("task", str(tmp_path), "strict_demo", "mock")

    store.update_run_status(run_id, RunStatus.SUCCEEDED)

    assert store.get_run(run_id)["finished_at"] is not None


def test_structured_event_and_memory_values_are_redacted_at_persistence(
    tmp_path: Path, monkeypatch
) -> None:
    exact_token = "exact-provider-token-for-redaction-test"
    monkeypatch.setenv("OPENAI_API_KEY", exact_token)
    store = SqliteStore(
        tmp_path / "agent.db", credential_snapshot=CredentialService().resolve()
    )
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


def test_docker_secret_token_is_redacted_before_event_persistence(tmp_path: Path, monkeypatch) -> None:
    token = "docker-secret-token-for-persistence-test"
    secret = tmp_path / "openai_api_key"
    secret.write_text(f"{token}\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY_FILE", str(secret))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    store = SqliteStore(
        tmp_path / "agent.db", credential_snapshot=CredentialService().resolve()
    )
    run_id = store.create_run("task", str(tmp_path), "strict_demo", "mock")

    store.append_event(run_id, "llm.output", {"raw": f"provider returned {token}"})

    with sqlite3.connect(store.db_path) as conn:
        persisted = conn.execute("select payload_json from events").fetchone()[0]
    assert token not in persisted
    assert "provider_token:redacted" in persisted


def test_injected_keyring_token_is_redacted_before_event_persistence(
    tmp_path: Path, monkeypatch
) -> None:
    token = "keyring-token-for-persistence-test"
    monkeypatch.delenv("OPENAI_API_KEY_FILE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    snapshot = CredentialService(keyring_backend=FakeKeyring(token)).resolve()
    store = SqliteStore(tmp_path / "agent.db", credential_snapshot=snapshot)
    run_id = store.create_run("task", str(tmp_path), "strict_demo", "mock")

    store.append_event(run_id, "llm.output", {"raw": f"provider returned {token}"})

    with sqlite3.connect(store.db_path) as conn:
        persisted = conn.execute("select payload_json from events").fetchone()[0]
    assert token not in persisted
    assert "provider_token:redacted" in persisted
