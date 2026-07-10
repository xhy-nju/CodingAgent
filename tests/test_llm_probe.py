from __future__ import annotations

import json

from coding_agent.llm import RealLLMProvider
from coding_agent.llm_probe import probe_real_llm


TEST_TOKEN = "provider-token-for-test"


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
    raw = json.dumps(
        {
            "kind": "final",
            "args": {},
            "reason": "real llm probe",
            "expectation": "stop",
        }
    )
    monkeypatch.setattr(provider, "next_action", lambda context: raw)

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
