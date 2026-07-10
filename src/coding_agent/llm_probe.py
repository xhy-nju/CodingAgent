from __future__ import annotations

import time
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict

from coding_agent.action_parser import parse_action
from coding_agent.domain import ActionKind
from coding_agent.llm import LLMContext, RealLLMProvider


ProbeErrorCode = Literal[
    "real_llm_disabled",
    "api_key_missing",
    "authentication_failed",
    "model_or_endpoint_not_found",
    "provider_rejected_request",
    "provider_unavailable",
    "request_timeout",
    "network_error",
    "invalid_provider_response",
    "protocol_error",
]


class LLMProbeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    provider: str
    base_url: str
    model: str
    latency_ms: int
    protocol_valid: bool
    action_kind: str | None = None
    error_code: ProbeErrorCode | None = None
    message: str


def _http_failure(status_code: int) -> tuple[ProbeErrorCode, str]:
    if status_code in {401, 403}:
        return "authentication_failed", "Provider rejected the configured credentials"
    if status_code == 404:
        return "model_or_endpoint_not_found", "Provider model or endpoint was not found"
    if 400 <= status_code < 500:
        return "provider_rejected_request", f"Provider rejected the probe request (HTTP {status_code})"
    return "provider_unavailable", f"Provider is unavailable (HTTP {status_code})"


def _result(
    provider: RealLLMProvider,
    started_ns: int,
    *,
    ok: bool,
    protocol_valid: bool,
    message: str,
    action_kind: str | None = None,
    error_code: ProbeErrorCode | None = None,
) -> LLMProbeResult:
    return LLMProbeResult(
        ok=ok,
        provider="openai-compatible",
        base_url=provider.base_url,
        model=provider.model,
        latency_ms=max(0, (time.perf_counter_ns() - started_ns) // 1_000_000),
        protocol_valid=protocol_valid,
        action_kind=action_kind,
        error_code=error_code,
        message=message,
    )


def probe_real_llm(provider: RealLLMProvider) -> LLMProbeResult:
    started_ns = time.perf_counter_ns()
    if not provider.enabled:
        return _result(
            provider,
            started_ns,
            ok=False,
            protocol_valid=False,
            error_code="real_llm_disabled",
            message="Real LLM is disabled",
        )
    if not provider.provider_token:
        return _result(
            provider,
            started_ns,
            ok=False,
            protocol_valid=False,
            error_code="api_key_missing",
            message="OPENAI_API_KEY is not configured",
        )
    try:
        raw = provider.next_action(
            LLMContext(
                task=(
                    "Connectivity check. Return exactly this JSON object and nothing else: "
                    '{"kind":"final","args":{},"reason":"real llm probe",'
                    '"expectation":"stop"}'
                ),
                step_index=0,
                feedback=[],
            )
        )
    except httpx.HTTPStatusError as exc:
        error_code, message = _http_failure(exc.response.status_code)
        return _result(
            provider,
            started_ns,
            ok=False,
            protocol_valid=False,
            error_code=error_code,
            message=message,
        )
    except httpx.TimeoutException:
        return _result(
            provider,
            started_ns,
            ok=False,
            protocol_valid=False,
            error_code="request_timeout",
            message="Real LLM probe timed out",
        )
    except httpx.RequestError:
        return _result(
            provider,
            started_ns,
            ok=False,
            protocol_valid=False,
            error_code="network_error",
            message="Real LLM provider could not be reached",
        )
    except (KeyError, IndexError, TypeError, ValueError):
        return _result(
            provider,
            started_ns,
            ok=False,
            protocol_valid=False,
            error_code="invalid_provider_response",
            message="Provider returned an invalid OpenAI-compatible response",
        )
    parsed = parse_action(raw)
    if not parsed.ok:
        return _result(
            provider,
            started_ns,
            ok=False,
            protocol_valid=False,
            error_code="protocol_error",
            message="Provider response failed the CodingAgent Action Protocol",
        )

    action = parsed.action
    assert action is not None
    if action.kind is not ActionKind.FINAL:
        return _result(
            provider,
            started_ns,
            ok=False,
            protocol_valid=False,
            action_kind=action.kind.value,
            error_code="protocol_error",
            message="Probe response must be a final action",
        )

    return _result(
        provider,
        started_ns,
        ok=True,
        protocol_valid=True,
        action_kind=action.kind.value,
        message="Real LLM probe succeeded",
    )
