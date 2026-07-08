from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CredentialService:
    provider_token: str | None
    base_url: str
    model: str
    real_enabled: bool

    @classmethod
    def from_env(cls) -> "CredentialService":
        return cls(
            provider_token=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL", "https://njusehub.info/v1"),
            model=os.environ.get("OPENAI_MODEL", "glm-5.2"),
            real_enabled=os.environ.get("ENABLE_REAL_LLM", "false").lower() == "true",
        )

    def status(self) -> dict[str, object]:
        return {
            "provider": "openai-compatible",
            "configured": bool(self.provider_token),
            "source": "environment" if self.provider_token else "missing",
            "base_url": self.base_url,
            "model": self.model,
            "real_enabled": self.real_enabled,
        }
