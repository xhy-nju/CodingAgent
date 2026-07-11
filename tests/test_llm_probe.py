from __future__ import annotations

import json

import httpx
import pytest

from coding_agent.llm import RealLLMProvider
from coding_agent.llm_probe import probe_real_llm


TEST_TOKEN = "provider-token-for-test"
HTTP_STATUS_ERROR_TEXT = "raw-http-status-provider-failure"
RESPONSE_BODY = "raw-response-body-provider-token-for-test"
AUTHORIZATION_HEADER = "Bearer raw-authorization-provider-token-for-test"


def make_provider(
    *,
    enabled: bool = True,
    token: str | None = TEST_TOKEN,
) -> RealLLMProvider:
    return RealLLMProvider(
        provider_token=token,
        base_url="https://example.test/v1",
        model="demo-model",
        enabled=enabled,
    )


def test_probe_accepts_strict_final_action_without_exposing_raw_content(monkeypatch) -> None:
    provider = make_provider()
    contexts = []
    raw = json.dumps(
        {
            "kind": "final",
            "args": {},
            "reason": "real llm probe",
            "expectation": "stop",
        }
    )
    def capture(context) -> str:
        contexts.append(context)
        return raw

    monkeypatch.setattr(provider, "next_action", capture)

    result = probe_real_llm(provider)

    assert result.ok is True
    assert result.provider == "openai-compatible"
    assert result.base_url == "https://example.test/v1"
    assert result.model == "demo-model"
    assert result.latency_ms >= 0
    assert result.protocol_valid is True
    assert result.action_kind == "final"
    assert result.error_code is None
    assert result.message == "Real LLM probe succeeded"
    assert contexts[0].max_completion_tokens == 256
    assert raw not in result.model_dump_json()
    assert TEST_TOKEN not in result.model_dump_json()


def test_probe_rejects_malformed_action_without_echoing_it(monkeypatch) -> None:
    provider = make_provider()
    raw = "not-json-provider-token-for-test"
    monkeypatch.setattr(provider, "next_action", lambda context: raw)

    result = probe_real_llm(provider)

    assert result.ok is False
    assert result.protocol_valid is False
    assert result.action_kind is None
    assert result.error_code == "protocol_error"
    assert result.message == "Provider response failed the CodingAgent Action Protocol"
    assert raw not in result.model_dump_json()
    assert TEST_TOKEN not in result.model_dump_json()


def test_probe_rejects_valid_non_final_action(monkeypatch) -> None:
    provider = make_provider()
    raw = json.dumps(
        {
            "kind": "tool",
            "tool": "list_files",
            "args": {},
            "reason": "inspect files",
            "expectation": "file list",
        }
    )
    monkeypatch.setattr(provider, "next_action", lambda context: raw)

    result = probe_real_llm(provider)

    assert result.ok is False
    assert result.protocol_valid is False
    assert result.action_kind == "tool"
    assert result.error_code == "protocol_error"
    assert result.message == "Probe response must be a final action"


@pytest.mark.parametrize(
    "raw",
    [
        '{"kind":"final","tool":"read_file","args":{},"reason":"x","expectation":"y"}',
        '{"kind":"final","args":{"path":"x"},"reason":"x","expectation":"y"}',
    ],
)
def test_probe_rejects_adversarial_final_action_shapes(monkeypatch, raw: str) -> None:
    provider = make_provider()
    monkeypatch.setattr(provider, "next_action", lambda context: raw)

    result = probe_real_llm(provider)

    assert result.ok is False
    assert result.error_code == "protocol_error"


@pytest.mark.parametrize("raw", [None, "", "   ", 42])
def test_probe_classifies_invalid_content_as_provider_response(
    monkeypatch, raw: object
) -> None:
    provider = make_provider()
    monkeypatch.setattr(provider, "next_action", lambda context: raw)

    result = probe_real_llm(provider)

    assert result.ok is False
    assert result.error_code == "invalid_provider_response"


def test_probe_refuses_when_real_llm_is_disabled(monkeypatch) -> None:
    provider = make_provider(enabled=False)
    calls: list[object] = []

    def fail_if_called(context) -> str:
        calls.append(context)
        raise AssertionError("next_action must not be called when the real LLM is disabled")

    monkeypatch.setattr(provider, "next_action", fail_if_called)

    result = probe_real_llm(provider)

    assert result.ok is False
    assert result.error_code == "real_llm_disabled"
    assert result.message == "Real LLM is disabled"
    assert calls == []


def test_probe_refuses_when_api_key_is_missing(monkeypatch) -> None:
    provider = make_provider(token=None)
    calls: list[object] = []

    def fail_if_called(context) -> str:
        calls.append(context)
        raise AssertionError("next_action must not be called when the API key is missing")

    monkeypatch.setattr(provider, "next_action", fail_if_called)

    result = probe_real_llm(provider)

    assert result.ok is False
    assert result.error_code == "api_key_missing"
    assert result.message == "OPENAI_API_KEY is not configured"
    assert calls == []


@pytest.mark.parametrize(
    ("status_code", "error_code", "message"),
    [
        (401, "authentication_failed", "Provider rejected the configured credentials"),
        (403, "authentication_failed", "Provider rejected the configured credentials"),
        (404, "model_or_endpoint_not_found", "Provider model or endpoint was not found"),
        (400, "provider_rejected_request", "Provider rejected the probe request (HTTP 400)"),
        (503, "provider_unavailable", "Provider is unavailable (HTTP 503)"),
    ],
)
def test_probe_classifies_http_status_without_leaking_token(
    monkeypatch,
    status_code: int,
    error_code: str,
    message: str,
) -> None:
    provider = make_provider()
    request = httpx.Request(
        "POST",
        "https://example.test/v1/chat/completions",
        headers={"Authorization": AUTHORIZATION_HEADER},
    )
    response = httpx.Response(status_code, content=RESPONSE_BODY, request=request)

    def fail(context) -> str:
        raise httpx.HTTPStatusError(HTTP_STATUS_ERROR_TEXT, request=request, response=response)

    monkeypatch.setattr(provider, "next_action", fail)

    result = probe_real_llm(provider)
    serialized = result.model_dump_json()

    assert result.ok is False
    assert result.error_code == error_code
    assert result.message == message
    assert TEST_TOKEN not in serialized
    assert HTTP_STATUS_ERROR_TEXT not in serialized
    assert RESPONSE_BODY not in serialized
    assert AUTHORIZATION_HEADER not in serialized


@pytest.mark.parametrize(
    ("error", "error_code", "message", "sensitive_text"),
    [
        (
            httpx.ReadTimeout(
                "raw-timeout-provider-token-for-test",
                request=httpx.Request("POST", "https://example.test/v1/chat/completions"),
            ),
            "request_timeout",
            "Real LLM probe timed out",
            "raw-timeout-provider-token-for-test",
        ),
        (
            httpx.ConnectError(
                "raw-network-provider-token-for-test",
                request=httpx.Request("POST", "https://example.test/v1/chat/completions"),
            ),
            "network_error",
            "Real LLM provider could not be reached",
            "raw-network-provider-token-for-test",
        ),
        (
            KeyError("raw-invalid-envelope-provider-token-for-test"),
            "invalid_provider_response",
            "Provider returned an invalid OpenAI-compatible response",
            "raw-invalid-envelope-provider-token-for-test",
        ),
    ],
)
def test_probe_classifies_transport_and_envelope_errors_without_leaking_token(
    monkeypatch,
    error: Exception,
    error_code: str,
    message: str,
    sensitive_text: str,
) -> None:
    provider = make_provider()

    def fail(context) -> str:
        raise error

    monkeypatch.setattr(provider, "next_action", fail)

    result = probe_real_llm(provider)
    serialized = result.model_dump_json()

    assert result.ok is False
    assert result.error_code == error_code
    assert result.message == message
    assert TEST_TOKEN not in serialized
    assert sensitive_text not in serialized
