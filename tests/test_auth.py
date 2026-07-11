from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from coding_agent.api import create_app
from coding_agent.auth import AuthService


def _auth() -> AuthService:
    return AuthService(
        admin_password="correct-password",
        session_secret="session-secret-that-is-long-enough",
        ttl_seconds=3600,
    )


def test_signed_session_round_trip_and_expiry() -> None:
    auth = _auth()
    token = auth.issue_session(now=100)

    active = auth.verify_session(token, now=101)
    expired = auth.verify_session(token, now=3700)

    assert active.authenticated is True
    assert active.expires_at == 3700
    assert expired.authenticated is False


def test_tampered_session_is_rejected() -> None:
    auth = _auth()
    token = auth.issue_session(now=100)

    assert auth.verify_session(f"{token}x", now=101).authenticated is False


def test_login_sets_secure_session_attributes(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, auth_service=_auth()))

    response = client.post("/api/auth/login", json={"password": "correct-password"})

    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert "coding_agent_session=" in cookie


def test_login_rejects_wrong_password_without_configuration_details(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, auth_service=_auth()))

    response = client.post("/api/auth/login", json={"password": "wrong-password"})

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid credentials"}


def test_auth_status_and_logout_use_session_cookie(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, auth_service=_auth()))
    client.post("/api/auth/login", json={"password": "correct-password"})

    authenticated = client.get("/api/auth/status")
    logged_out = client.post("/api/auth/logout")
    after_logout = client.get("/api/auth/status")

    assert authenticated.json()["authenticated"] is True
    assert logged_out.json() == {"authenticated": False, "expires_at": None}
    assert after_logout.json()["authenticated"] is False


def test_admin_routes_require_session_while_mock_stays_public(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, auth_service=_auth()))

    assert client.post("/api/runs/demo", json={"name": "bugfix"}).status_code == 200
    assert client.get("/api/policies").status_code == 200
    assert client.get("/api/credentials/status").status_code == 200
    assert client.get("/api/memory").status_code == 401
    assert client.get("/api/approvals").status_code == 401


def test_authenticated_cross_origin_admin_write_is_rejected(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path, auth_service=_auth()))
    client.post("/api/auth/login", json={"password": "correct-password"})

    response = client.post(
        "/api/approvals/approval-1/decision",
        headers={"Origin": "https://attacker.example"},
        json={"decision": "reject", "reviewer": "admin", "reason": "unsafe"},
    )

    assert response.status_code == 403

