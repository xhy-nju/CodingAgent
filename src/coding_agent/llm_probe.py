from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, ConfigDict

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


def probe_real_llm(provider: RealLLMProvider) -> LLMProbeResult:
    started_ns = time.perf_counter_ns()
    provider.next_action(
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
    latency_ms = max(0, (time.perf_counter_ns() - started_ns) // 1_000_000)
    return LLMProbeResult(
        ok=True,
        provider="openai-compatible",
        base_url=provider.base_url,
        model=provider.model,
        latency_ms=latency_ms,
        protocol_valid=True,
        action_kind="final",
        message="Real LLM probe succeeded",
    )
