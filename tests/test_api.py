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
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get("/api/credentials/status")

    assert response.status_code == 200
    assert response.json() == {
        "provider": "openai-compatible",
        "configured": True,
        "real_enabled": True,
    }


def test_approval_decision_endpoint_records_state(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post("/api/approvals/approval-1/decision")

    assert response.status_code == 200
    assert response.json() == {"approval_id": "approval-1", "state": "recorded"}
