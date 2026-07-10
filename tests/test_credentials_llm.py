from __future__ import annotations

from typing import Any

import pytest

from coding_agent.credentials import CredentialService
from coding_agent.llm import LLMContext, RealLLMProvider


def test_credential_status_without_key(monkeypatch) -> None:
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
    assert captured["json"]["messages"][1]["content"] == "Task: fix tests\nStep: 2"
    assert captured["json"]["max_tokens"] == 512
    assert captured["timeout"] == 30


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
