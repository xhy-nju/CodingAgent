from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

import keyring
from keyring.errors import KeyringError, PasswordDeleteError


class KeyringBackend(Protocol):
    def get_password(self, service: str, username: str) -> str | None: ...

    def set_password(self, service: str, username: str, token: str) -> None: ...

    def delete_password(self, service: str, username: str) -> None: ...


@dataclass(frozen=True)
class CredentialSnapshot:
    provider_token: str | None
    source: Literal["docker-secret", "environment", "keyring", "missing"]
    base_url: str
    model: str
    real_enabled: bool

    @property
    def configured(self) -> bool:
        return bool(self.provider_token)


class CredentialService:
    SERVICE_NAME = "coding-agent"
    USERNAME = "openai-compatible"

    def __init__(self, keyring_backend: KeyringBackend = keyring) -> None:
        self.keyring_backend = keyring_backend

    @classmethod
    def from_env(cls) -> "CredentialService":
        return cls()

    def resolve(self) -> CredentialSnapshot:
        file_name = os.environ.get("OPENAI_API_KEY_FILE")
        if file_name:
            path = Path(file_name)
            if path.stat().st_size > 16 * 1024:
                raise ValueError("credential file exceeds 16 KiB")
            token = path.read_text(encoding="utf-8").strip()
            if token:
                return self._snapshot(token, "docker-secret")
        token = os.environ.get("OPENAI_API_KEY", "").strip()
        if token:
            return self._snapshot(token, "environment")
        try:
            token = self.keyring_backend.get_password(self.SERVICE_NAME, self.USERNAME)
        except KeyringError:
            return self._snapshot(None, "missing")
        normalized = (token.strip() or None) if token else None
        return self._snapshot(normalized, "keyring" if normalized else "missing")

    def set_keyring_token(self, token: str) -> None:
        normalized = token.strip()
        if not normalized:
            raise ValueError("API key cannot be empty")
        self.keyring_backend.set_password(self.SERVICE_NAME, self.USERNAME, normalized)

    def clear_keyring_token(self) -> bool:
        try:
            self.keyring_backend.delete_password(self.SERVICE_NAME, self.USERNAME)
        except PasswordDeleteError:
            return False
        return True

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

    def _snapshot(
        self,
        provider_token: str | None,
        source: Literal["docker-secret", "environment", "keyring", "missing"],
    ) -> CredentialSnapshot:
        return CredentialSnapshot(
            provider_token=provider_token,
            source=source,
            base_url=os.environ.get("OPENAI_BASE_URL", "https://njusehub.info/v1"),
            model=os.environ.get("OPENAI_MODEL", "glm-5.2"),
            real_enabled=os.environ.get("ENABLE_REAL_LLM", "false").lower() == "true",
        )
