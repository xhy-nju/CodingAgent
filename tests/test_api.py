from pathlib import Path

from keyring.errors import PasswordDeleteError
from starlette.testclient import TestClient

from coding_agent.api import create_app
from coding_agent.auth import AuthService
from coding_agent.credentials import CredentialService, CredentialSnapshot
from coding_agent.memory import MemoryService
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


def authenticated_client(tmp_path: Path) -> TestClient:
    auth = AuthService(
        admin_password="test-admin-password",
        session_secret="test-session-secret-that-is-long-enough",
    )
    client = TestClient(create_app(data_dir=tmp_path, auth_service=auth))
    response = client.post(
        "/api/auth/login", json={"password": "test-admin-password"}
    )
    assert response.status_code == 200
    return client


def test_create_bugfix_demo_run(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post("/api/runs/demo", json={"name": "bugfix"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["run_id"].startswith("run-")


def test_demo_workspace_is_created_inside_runtime_dir(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post("/api/runs/demo", json={"name": "bugfix"})

    assert response.status_code == 200
    demo_root = tmp_path / "demo-workspaces"
    assert demo_root.exists()
    assert any(path.name == "workspace" for path in demo_root.glob("coding-agent-demo-*/workspace"))


def test_events_endpoint_returns_sse_lines(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))
    run = client.post("/api/runs/demo", json={"name": "bugfix"}).json()

    response = client.get(f"/api/runs/{run['run_id']}/events")

    assert response.status_code == 200
    assert "event: run.started" in response.text
    assert "event: guardrail.checked" in response.text
    assert "event: tool.result" in response.text
    assert "event: feedback.recorded" in response.text
    assert "event: llm.raw" not in response.text
    assert "event: feedback\n" not in response.text
    assert "data:" in response.text


def test_policy_endpoint_lists_profiles(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get("/api/policies")

    assert response.status_code == 200
    assert "strict_demo" in response.json()["profiles"]


def test_credential_status_reflects_environment(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "provider-token-for-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "demo-model")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get("/api/credentials/status")

    assert response.status_code == 200
    assert response.json() == {
        "provider": "openai-compatible",
        "configured": True,
        "source": "environment",
        "base_url": "https://example.test/v1",
        "model": "demo-model",
        "real_enabled": True,
    }


def test_credential_status_resolves_once(tmp_path: Path) -> None:
    snapshot = CredentialSnapshot(
        provider_token="status-token",
        source="keyring",
        base_url="https://example.test/v1",
        model="demo-model",
        real_enabled=True,
    )

    class CountingCredentials:
        def __init__(self) -> None:
            self.resolve_calls = 0

        def resolve(self) -> CredentialSnapshot:
            self.resolve_calls += 1
            return snapshot

        def status(self, snapshot: CredentialSnapshot | None = None) -> dict[str, object]:
            snapshot = snapshot or self.resolve()
            return {
                "provider": "openai-compatible",
                "configured": snapshot.configured,
                "source": snapshot.source,
                "base_url": snapshot.base_url,
                "model": snapshot.model,
                "real_enabled": snapshot.real_enabled,
            }

    credentials = CountingCredentials()
    client = TestClient(create_app(data_dir=tmp_path, credential_service=credentials))

    response = client.get("/api/credentials/status")

    assert response.status_code == 200
    assert credentials.resolve_calls == 1


def test_approval_decision_endpoint_records_state(tmp_path: Path) -> None:
    client = authenticated_client(tmp_path)

    response = client.post(
        "/api/approvals/approval-does-not-exist/decision",
        json={"decision": "reject", "reviewer": "admin", "reason": "not approved"},
    )

    assert response.status_code == 404


def test_approval_decision_requires_explicit_review_input(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post("/api/approvals/approval-1/decision", json={})

    assert response.status_code == 422


def test_sse_never_exposes_exact_or_known_format_tokens(tmp_path: Path, monkeypatch) -> None:
    exact_token = "exact-sse-provider-token-for-test"
    monkeypatch.setenv("OPENAI_API_KEY", exact_token)
    store = SqliteStore(tmp_path / "agent.db")
    run_id = store.create_run("task", str(tmp_path), "strict_demo", "mock")
    store.append_event(
        run_id,
        "llm.output",
        {"raw": f"{exact_token} sk-sseknownformat123456789012345"},
    )
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get(f"/api/runs/{run_id}/events")

    assert response.status_code == 200
    assert exact_token not in response.text
    assert "sk-sseknownformat123456789012345" not in response.text
    assert "provider_token:redacted" in response.text


def test_sse_redacts_docker_secret_token(tmp_path: Path, monkeypatch) -> None:
    token = "docker-secret-token-for-sse-test"
    secret = tmp_path / "openai_api_key"
    secret.write_text(f"{token}\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY_FILE", str(secret))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    snapshot = CredentialService().resolve()
    store = SqliteStore(tmp_path / "agent.db", credential_snapshot=snapshot)
    run_id = store.create_run("task", str(tmp_path), "strict_demo", "mock")
    store.append_event(run_id, "llm.output", {"raw": f"provider returned {token}"})
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get(f"/api/runs/{run_id}/events")

    assert response.status_code == 200
    assert token not in response.text
    assert "provider_token:redacted" in response.text


def test_sse_redacts_injected_keyring_token(tmp_path: Path, monkeypatch) -> None:
    token = "keyring-token-for-sse-test"
    monkeypatch.delenv("OPENAI_API_KEY_FILE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    credentials = CredentialService(keyring_backend=FakeKeyring(token))
    snapshot = credentials.resolve()
    store = SqliteStore(tmp_path / "agent.db", credential_snapshot=snapshot)
    run_id = store.create_run("task", str(tmp_path), "strict_demo", "mock")
    store.append_event(run_id, "llm.output", {"raw": f"provider returned {token}"})
    client = TestClient(create_app(data_dir=tmp_path, credential_service=credentials))

    response = client.get(f"/api/runs/{run_id}/events")

    assert response.status_code == 200
    assert token not in response.text
    assert "provider_token:redacted" in response.text


def test_memory_endpoint_returns_real_scoped_records(tmp_path: Path) -> None:
    memory = MemoryService(SqliteStore(tmp_path / "agent.db"))
    memory.write_summary(
        scope="project",
        tags=["pytest"],
        content="Use the focused calculator test",
        source_run_id="run-1",
    )
    memory.write_summary(
        scope="other",
        tags=["pytest"],
        content="Not part of this project",
        source_run_id="run-2",
    )
    client = authenticated_client(tmp_path)

    response = client.get("/api/memory", params={"scope": "project", "query": "calculator"})

    assert response.status_code == 200
    assert [item["content"] for item in response.json()["records"]] == [
        "Use the focused calculator test"
    ]
