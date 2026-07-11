from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from keyring.errors import KeyringError, PasswordDeleteError

from coding_agent.credentials import CredentialService, CredentialSnapshot
from coding_agent.domain import FeedbackSignal, FeedbackType, MemoryRecord
from coding_agent.llm import LLMContext, LLMProviderError, RealLLMProvider


class FakeKeyring:
    def __init__(self, token: str | None = None) -> None:
        self.token = token

    def get_password(self, service: str, username: str) -> str | None:
        return self.token

    def set_password(self, service: str, username: str, token: str) -> None:
        self.token = token

    def delete_password(self, service: str, username: str) -> None:
        if self.token is None:
            raise PasswordDeleteError("credential not found")
        self.token = None


class UnavailableKeyring:
    def get_password(self, service: str, username: str) -> str | None:
        raise KeyringError("keyring is unavailable")

    def set_password(self, service: str, username: str, token: str) -> None:
        raise AssertionError("set_password is not used by this test")

    def delete_password(self, service: str, username: str) -> None:
        raise AssertionError("delete_password is not used by this test")


def test_credential_priority_prefers_secret_file(tmp_path, monkeypatch) -> None:
    secret = tmp_path / "openai_api_key"
    secret.write_text("file-token\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY_FILE", str(secret))
    monkeypatch.setenv("OPENAI_API_KEY", "environment-token")
    service = CredentialService(keyring_backend=FakeKeyring("keyring-token"))

    snapshot = service.resolve()

    assert snapshot.provider_token == "file-token"
    assert snapshot.source == "docker-secret"


def test_credential_priority_prefers_environment_over_keyring(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY_FILE", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "environment-token")
    service = CredentialService(keyring_backend=FakeKeyring("keyring-token"))

    snapshot = service.resolve()

    assert snapshot.provider_token == "environment-token"
    assert snapshot.source == "environment"


def test_credential_service_treats_blank_keyring_token_as_missing(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY_FILE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    service = CredentialService(keyring_backend=FakeKeyring("  "))

    snapshot = service.resolve()

    assert snapshot.provider_token is None
    assert snapshot.source == "missing"


def test_credential_service_treats_keyring_read_error_as_missing(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY_FILE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    service = CredentialService(keyring_backend=UnavailableKeyring())

    snapshot = service.resolve()

    assert snapshot.provider_token is None
    assert snapshot.source == "missing"


def test_keyring_set_update_and_clear(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY_FILE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    keyring = FakeKeyring()
    service = CredentialService(keyring_backend=keyring)

    service.set_keyring_token("first-token")
    service.set_keyring_token("second-token")

    assert service.resolve().provider_token == "second-token"
    assert service.clear_keyring_token() is True
    assert service.resolve().configured is False
    assert service.clear_keyring_token() is False


def test_credential_service_rejects_oversized_secret_and_empty_keyring_token(tmp_path, monkeypatch) -> None:
    secret = tmp_path / "openai_api_key"
    secret.write_text("x" * (16 * 1024 + 1), encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY_FILE", str(secret))
    service = CredentialService(keyring_backend=FakeKeyring())

    with pytest.raises(ValueError, match="credential file exceeds 16 KiB"):
        service.resolve()
    with pytest.raises(ValueError, match="API key cannot be empty"):
        service.set_keyring_token("  ")


def test_real_provider_uses_credential_snapshot() -> None:
    snapshot = CredentialSnapshot(
        provider_token="snapshot-token",
        source="keyring",
        base_url="https://example.test/v1/",
        model="snapshot-model",
        real_enabled=True,
    )

    provider = RealLLMProvider.from_credentials(snapshot)

    assert provider.provider_token == "snapshot-token"
    assert provider.base_url == "https://example.test/v1"
    assert provider.model == "snapshot-model"
    assert provider.enabled is True


def test_credential_status_without_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY_FILE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setenv("ENABLE_REAL_LLM", "false")

    status = CredentialService.from_env().status()

    assert status == {
        "provider": "openai-compatible",
        "configured": False,
        "source": "missing",
        "base_url": "https://njusehub.info/v1",
        "model": "glm-5.2",
        "real_enabled": False,
    }


def test_credential_status_with_key_and_overrides(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY_FILE", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "provider-token-for-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "demo-model")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")

    status = CredentialService.from_env().status()

    assert status == {
        "provider": "openai-compatible",
        "configured": True,
        "source": "environment",
        "base_url": "https://example.test/v1",
        "model": "demo-model",
        "real_enabled": True,
    }
    assert "provider-token-for-test" not in str(status)


def test_real_provider_refuses_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "demo-token-value-not-real")
    monkeypatch.setenv("ENABLE_REAL_LLM", "false")
    provider = RealLLMProvider.from_env()

    try:
        provider.next_action(LLMContext(task="x", step_index=0, feedback=[]))
    except RuntimeError as exc:
        assert "ENABLE_REAL_LLM" in str(exc)
    else:
        raise AssertionError("provider should refuse when disabled")


def test_real_provider_posts_openai_compatible_request(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"choices": [{"message": {"content": "{\"kind\":\"final\"}"}}]}

    def fake_post(
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
        timeout: int,
    ) -> FakeResponse:
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setenv("OPENAI_API_KEY", "provider-token-for-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("OPENAI_MODEL", "demo-model")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setattr("coding_agent.llm.httpx.post", fake_post)

    provider = RealLLMProvider.from_env()
    action = provider.next_action(LLMContext(task="fix tests", step_index=2, feedback=[]))

    assert action == "{\"kind\":\"final\"}"
    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert captured["headers"] == {"Authorization": "Bearer provider-token-for-test"}
    assert captured["json"]["model"] == "demo-model"
    system_message = captured["json"]["messages"][0]["content"]
    user_message = captured["json"]["messages"][1]["content"]
    assert "Return exactly one JSON object" in system_message
    assert "run_tests" in system_message
    assert "write_file" in system_message
    assert "Task: fix tests" in user_message
    assert "Step: 2/8" in user_message
    assert captured["json"]["max_tokens"] == 512
    assert captured["timeout"] == 30


def test_real_provider_redacts_context_values_before_constructing_messages(monkeypatch) -> None:
    token = "provider-token-for-message-redaction-test"
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"choices": [{"message": {"content": "{\"kind\":\"final\"}"}}]}

    def fake_post(
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
        timeout: int,
    ) -> FakeResponse:
        captured["messages"] = json["messages"]
        return FakeResponse()

    feedback = FeedbackSignal(
        type=FeedbackType.TEST_FAILED,
        severity="error",
        summary=f"feedback summary {token}",
        details={"raw": token},
    )
    memory = MemoryRecord(
        id="mem-1",
        scope="project",
        kind="summary",
        tags=["provider"],
        content=f"memory content {token}",
        source_run_id=None,
        confidence=1.0,
        sensitive=False,
    )
    context = LLMContext(
        task=f"task {token}",
        step_index=2,
        feedback=[feedback],
        memories=(memory,),
    )
    provider = RealLLMProvider(
        provider_token=token,
        base_url="https://example.test/v1",
        model="demo-model",
        enabled=True,
    )
    monkeypatch.setattr("coding_agent.llm.httpx.post", fake_post)

    provider.next_action(context)

    serialized = json.dumps(captured["messages"])
    assert token not in serialized
    assert "provider_token:redacted" in serialized
    assert "Feedback:" in captured["messages"][1]["content"]
    assert feedback.summary.endswith(token)
    assert feedback.details["raw"] == token
    assert memory.content.endswith(token)


def test_real_provider_converts_timeout_to_stable_error(monkeypatch) -> None:
    def timeout(*args, **kwargs):
        raise httpx.TimeoutException("secret response body")

    monkeypatch.setattr("coding_agent.llm.httpx.post", timeout)
    provider = RealLLMProvider(
        provider_token="provider-token-for-test",
        base_url="https://example.test/v1",
        model="demo-model",
        enabled=True,
    )

    with pytest.raises(LLMProviderError, match="timed out") as error:
        provider.next_action(LLMContext(task="probe", step_index=0, feedback=[]))

    assert "secret response body" not in str(error.value)


def test_real_provider_rejects_missing_choices_without_response_dump(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"provider_debug": "must-not-be-exposed"}

    monkeypatch.setattr("coding_agent.llm.httpx.post", lambda *args, **kwargs: FakeResponse())
    provider = RealLLMProvider(
        provider_token="provider-token-for-test",
        base_url="https://example.test/v1",
        model="demo-model",
        enabled=True,
    )

    with pytest.raises(LLMProviderError, match="invalid response") as error:
        provider.next_action(LLMContext(task="probe", step_index=0, feedback=[]))

    assert "must-not-be-exposed" not in str(error.value)


@pytest.mark.parametrize("content", [None, "", "   ", 42])
def test_real_provider_rejects_null_empty_or_non_string_content(
    monkeypatch, content: object
) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr("coding_agent.llm.httpx.post", lambda *args, **kwargs: FakeResponse())
    provider = RealLLMProvider(
        provider_token="provider-token-for-test",
        base_url="https://example.test/v1",
        model="demo-model",
        enabled=True,
    )

    with pytest.raises(ValueError, match="non-empty string"):
        provider.next_action(LLMContext(task="probe", step_index=0, feedback=[]))
