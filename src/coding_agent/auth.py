from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SessionStatus:
    authenticated: bool
    expires_at: int | None = None


class AuthService:
    COOKIE_NAME = "coding_agent_session"

    def __init__(
        self,
        admin_password: str,
        session_secret: str,
        *,
        ttl_seconds: int = 8 * 60 * 60,
        cookie_secure: bool = False,
    ) -> None:
        self.admin_password = admin_password
        self.session_secret = session_secret
        self.ttl_seconds = ttl_seconds
        self.cookie_secure = cookie_secure

    @classmethod
    def from_env(cls) -> "AuthService":
        return cls(
            admin_password=os.environ.get("ADMIN_PASSWORD", ""),
            session_secret=os.environ.get("SESSION_SECRET", ""),
            ttl_seconds=int(os.environ.get("SESSION_TTL_SECONDS", str(8 * 60 * 60))),
            cookie_secure=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
        )

    def verify_password(self, candidate: str) -> bool:
        return bool(self.admin_password) and hmac.compare_digest(
            candidate, self.admin_password
        )

    def issue_session(self, *, now: int | None = None) -> str:
        if len(self.session_secret) < 32:
            raise RuntimeError("session signing is not configured")
        issued_at = int(time.time()) if now is None else now
        payload = {
            "issued_at": issued_at,
            "expires_at": issued_at + self.ttl_seconds,
            "session_id": secrets.token_urlsafe(18),
        }
        encoded = self._encode(json.dumps(payload, separators=(",", ":")).encode())
        return f"{encoded}.{self._signature(encoded)}"

    def verify_session(self, token: str | None, *, now: int | None = None) -> SessionStatus:
        if not token or len(self.session_secret) < 32:
            return SessionStatus(authenticated=False)
        try:
            encoded, supplied_signature = token.split(".", maxsplit=1)
            if not hmac.compare_digest(supplied_signature, self._signature(encoded)):
                return SessionStatus(authenticated=False)
            payload: dict[str, Any] = json.loads(self._decode(encoded))
            expires_at = int(payload["expires_at"])
            session_id = payload["session_id"]
            issued_at = int(payload["issued_at"])
            current_time = int(time.time()) if now is None else now
            if not isinstance(session_id, str) or not session_id or issued_at > current_time:
                return SessionStatus(authenticated=False)
            if current_time >= expires_at:
                return SessionStatus(authenticated=False)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return SessionStatus(authenticated=False)
        return SessionStatus(authenticated=True, expires_at=expires_at)

    def _signature(self, encoded_payload: str) -> str:
        digest = hmac.new(
            self.session_secret.encode(), encoded_payload.encode(), hashlib.sha256
        ).digest()
        return self._encode(digest)

    @staticmethod
    def _encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    @staticmethod
    def _decode(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.b64decode(
            value + padding, altchars=b"-_", validate=True
        )

