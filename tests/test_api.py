from pathlib import Path

from starlette.testclient import TestClient

from coding_agent.api import create_app


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


def test_approval_decision_endpoint_records_state(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post(
        "/api/approvals/approval-does-not-exist/decision",
        json={"decision": "reject", "reviewer": "admin", "reason": "not approved"},
    )

    assert response.status_code == 404


def test_approval_decision_requires_explicit_review_input(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post("/api/approvals/approval-1/decision", json={})

    assert response.status_code == 422
