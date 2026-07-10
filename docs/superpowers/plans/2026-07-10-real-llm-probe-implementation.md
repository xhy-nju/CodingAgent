# Real LLM Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe `python -m coding_agent llm probe` command that performs one real OpenAI-compatible request, validates a strict final Action, and reports a sanitized structured result without executing tools.

**Architecture:** A new `llm_probe` service owns probe orchestration, strict Action validation, latency measurement, and provider error classification. The Typer CLI constructs `RealLLMProvider` from server-side environment variables and serializes the service result; it never accepts or prints credentials. The existing Mock demos and Agent Loop remain unchanged.

**Tech Stack:** Python 3.11+, Pydantic v2, Typer, HTTPX, pytest, Docker Compose.

## Global Constraints

- Follow TDD for every behavior: add one failing test, verify the expected failure, implement minimally, then rerun.
- Do not contact a real network from automated tests.
- Do not add an API or browser endpoint in this increment.
- Do not construct `AgentLoop` or a tool dispatcher from the probe path.
- Read credentials only from `RealLLMProvider.from_env()`.
- Never include the API key, Authorization header, or raw model content in probe output or error messages.
- A successful probe must receive one strict Action with `kind="final"`.
- Keep the existing `demo bugfix` and `demo dangerous-action` commands on `MockLLMProvider`.

---

### Task 1: Successful Probe Service

**Files:**
- Create: `src/coding_agent/llm_probe.py`
- Create: `tests/test_llm_probe.py`

**Interfaces:**
- Consumes: `RealLLMProvider.next_action(context: LLMContext) -> str`.
- Produces: `LLMProbeResult` and `probe_real_llm(provider: RealLLMProvider) -> LLMProbeResult`.

- [ ] **Step 1: Write the failing success-path test**

Create `tests/test_llm_probe.py`:

```python
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
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
pytest tests/test_llm_probe.py::test_probe_accepts_strict_final_action_without_exposing_raw_content -v
```

Expected: collection fails with `ModuleNotFoundError: No module named 'coding_agent.llm_probe'`.

- [ ] **Step 3: Implement the minimal successful probe**

Create `src/coding_agent/llm_probe.py`:

```python
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
```

- [ ] **Step 4: Run the test and verify GREEN**

Run:

```powershell
pytest tests/test_llm_probe.py::test_probe_accepts_strict_final_action_without_exposing_raw_content -v
```

Expected: `1 passed`.

- [ ] **Step 5: Commit the successful service baseline**

```powershell
git add src/coding_agent/llm_probe.py tests/test_llm_probe.py
git commit -m "feat: add real llm probe service"
```

---

### Task 2: Strict Probe Protocol Validation

**Files:**
- Modify: `src/coding_agent/llm_probe.py`
- Modify: `tests/test_llm_probe.py`

**Interfaces:**
- Consumes: `parse_action(raw: str) -> ParseResult` and `ActionKind.FINAL`.
- Produces: `protocol_error` results for malformed or non-final responses.

- [ ] **Step 1: Add failing protocol tests**

Append to `tests/test_llm_probe.py`:

```python
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
```

- [ ] **Step 2: Run the protocol tests and verify RED**

Run:

```powershell
pytest tests/test_llm_probe.py -v
```

Expected: both new tests fail because the initial implementation reports every response as successful.

- [ ] **Step 3: Add strict parsing and a private result helper**

Replace `probe_real_llm` in `src/coding_agent/llm_probe.py` and add the imports/helper below:

```python
from coding_agent.action_parser import parse_action
from coding_agent.domain import ActionKind


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
```

- [ ] **Step 4: Run the protocol tests and verify GREEN**

Run:

```powershell
pytest tests/test_llm_probe.py -v
```

Expected: `3 passed`.

- [ ] **Step 5: Commit protocol validation**

```powershell
git add src/coding_agent/llm_probe.py tests/test_llm_probe.py
git commit -m "feat: validate llm probe protocol"
```

---

### Task 3: Configuration And Provider Error Classification

**Files:**
- Modify: `src/coding_agent/llm_probe.py`
- Modify: `tests/test_llm_probe.py`

**Interfaces:**
- Consumes: HTTPX exception types and `RealLLMProvider.enabled` / `provider_token`.
- Produces: sanitized stable probe errors defined by `ProbeErrorCode`.

- [ ] **Step 1: Add failing configuration tests**

Append to `tests/test_llm_probe.py`:

```python
def test_probe_refuses_when_real_llm_is_disabled() -> None:
    result = probe_real_llm(make_provider(enabled=False))

    assert result.ok is False
    assert result.error_code == "real_llm_disabled"
    assert result.message == "Real LLM is disabled"


def test_probe_refuses_when_api_key_is_missing() -> None:
    result = probe_real_llm(make_provider(token=None))

    assert result.ok is False
    assert result.error_code == "api_key_missing"
    assert result.message == "OPENAI_API_KEY is not configured"
```

- [ ] **Step 2: Run configuration tests and verify RED**

Run:

```powershell
pytest tests/test_llm_probe.py::test_probe_refuses_when_real_llm_is_disabled tests/test_llm_probe.py::test_probe_refuses_when_api_key_is_missing -v
```

Expected: both tests fail with the existing `RuntimeError` from `RealLLMProvider.next_action`.

- [ ] **Step 3: Add configuration gates before the request**

Add these checks immediately after `started_ns` in `probe_real_llm`:

```python
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
```

- [ ] **Step 4: Run configuration tests and verify GREEN**

Run:

```powershell
pytest tests/test_llm_probe.py -v
```

Expected: `5 passed`.

- [ ] **Step 5: Add failing provider exception tests**

Add `import httpx` and append to `tests/test_llm_probe.py`:

```python
import httpx
import pytest


@pytest.mark.parametrize(
    ("status_code", "error_code"),
    [
        (401, "authentication_failed"),
        (403, "authentication_failed"),
        (404, "model_or_endpoint_not_found"),
        (400, "provider_rejected_request"),
        (503, "provider_unavailable"),
    ],
)
def test_probe_classifies_http_status_without_leaking_token(
    monkeypatch,
    status_code: int,
    error_code: str,
) -> None:
    provider = make_provider()
    request = httpx.Request("POST", "https://example.test/v1/chat/completions")
    response = httpx.Response(status_code, request=request)

    def fail(context) -> str:
        raise httpx.HTTPStatusError("provider failure", request=request, response=response)

    monkeypatch.setattr(provider, "next_action", fail)

    result = probe_real_llm(provider)

    assert result.ok is False
    assert result.error_code == error_code
    assert TEST_TOKEN not in result.model_dump_json()


@pytest.mark.parametrize(
    ("error", "error_code"),
    [
        (
            httpx.ReadTimeout(
                "timeout provider-token-for-test",
                request=httpx.Request("POST", "https://example.test/v1/chat/completions"),
            ),
            "request_timeout",
        ),
        (
            httpx.ConnectError(
                "network provider-token-for-test",
                request=httpx.Request("POST", "https://example.test/v1/chat/completions"),
            ),
            "network_error",
        ),
        (KeyError("provider-token-for-test"), "invalid_provider_response"),
    ],
)
def test_probe_classifies_transport_and_envelope_errors_without_leaking_token(
    monkeypatch,
    error: Exception,
    error_code: str,
) -> None:
    provider = make_provider()

    def fail(context) -> str:
        raise error

    monkeypatch.setattr(provider, "next_action", fail)

    result = probe_real_llm(provider)

    assert result.ok is False
    assert result.error_code == error_code
    assert TEST_TOKEN not in result.model_dump_json()
```

- [ ] **Step 6: Run provider exception tests and verify RED**

Run:

```powershell
pytest tests/test_llm_probe.py -v
```

Expected: the exception tests fail because HTTPX and malformed-envelope exceptions escape the service.

- [ ] **Step 7: Implement sanitized exception classification**

Add `import httpx` to `src/coding_agent/llm_probe.py`. Add this helper:

```python
def _http_failure(status_code: int) -> tuple[ProbeErrorCode, str]:
    if status_code in {401, 403}:
        return "authentication_failed", "Provider rejected the configured credentials"
    if status_code == 404:
        return "model_or_endpoint_not_found", "Provider model or endpoint was not found"
    if 400 <= status_code < 500:
        return "provider_rejected_request", f"Provider rejected the probe request (HTTP {status_code})"
    return "provider_unavailable", f"Provider is unavailable (HTTP {status_code})"
```

Wrap the `provider.next_action` invocation in `probe_real_llm` with:

```python
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
```

- [ ] **Step 8: Run all probe tests and verify GREEN**

Run:

```powershell
pytest tests/test_llm_probe.py -v
```

Expected: `13 passed` because the status-code parameterization contributes five cases and the transport parameterization contributes three cases.

- [ ] **Step 9: Commit error classification**

```powershell
git add src/coding_agent/llm_probe.py tests/test_llm_probe.py
git commit -m "feat: classify real llm probe failures"
```

---

### Task 4: Typer CLI Probe Command

**Files:**
- Modify: `src/coding_agent/cli.py`
- Modify: `tests/test_cli.py`

**Interfaces:**
- Consumes: `RealLLMProvider.from_env()` and `probe_real_llm(provider)`.
- Produces: CLI `llm probe`, JSON stdout, exit code `0` on success and `1` on failure.

- [ ] **Step 1: Add the failing successful-command test**

Update imports in `tests/test_cli.py`:

```python
from coding_agent.llm import RealLLMProvider
```

Append:

```python
def test_llm_probe_command_outputs_sanitized_success(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "provider-token-for-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "demo-model")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setattr(
        RealLLMProvider,
        "next_action",
        lambda self, context: json.dumps(
            {
                "kind": "final",
                "args": {},
                "reason": "real llm probe",
                "expectation": "stop",
            }
        ),
    )
    runner = CliRunner()

    result = runner.invoke(app, ["llm", "probe"])

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["ok"] is True
    assert body["protocol_valid"] is True
    assert body["action_kind"] == "final"
    assert body["model"] == "demo-model"
    assert "provider-token-for-test" not in result.stdout
```

- [ ] **Step 2: Run the successful-command test and verify RED**

Run:

```powershell
pytest tests/test_cli.py::test_llm_probe_command_outputs_sanitized_success -v
```

Expected: failure because the `llm` command group does not exist.

- [ ] **Step 3: Implement the CLI group and command**

Update `src/coding_agent/cli.py` imports:

```python
from coding_agent.llm import MockLLMProvider, RealLLMProvider
from coding_agent.llm_probe import probe_real_llm
```

Register the group beside `credentials_app`:

```python
llm_app = typer.Typer(help="LLM provider commands")
app.add_typer(llm_app, name="llm")
```

Add the command after the credential commands:

```python
@llm_app.command("probe")
def llm_probe() -> None:
    result = probe_real_llm(RealLLMProvider.from_env())
    typer.echo(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
```

- [ ] **Step 4: Run the successful-command test and verify GREEN**

Run:

```powershell
pytest tests/test_cli.py::test_llm_probe_command_outputs_sanitized_success -v
```

Expected: `1 passed`.

- [ ] **Step 5: Add the failing disabled-command test**

Append to `tests/test_cli.py`:

```python
def test_llm_probe_command_exits_one_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "provider-token-for-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "demo-model")
    monkeypatch.setenv("ENABLE_REAL_LLM", "false")
    runner = CliRunner()

    result = runner.invoke(app, ["llm", "probe"])

    assert result.exit_code == 1
    body = json.loads(result.stdout)
    assert body["ok"] is False
    assert body["error_code"] == "real_llm_disabled"
    assert "provider-token-for-test" not in result.stdout
```

- [ ] **Step 6: Run the disabled-command test and verify RED**

Run:

```powershell
pytest tests/test_cli.py::test_llm_probe_command_exits_one_when_disabled -v
```

Expected: failure because the command currently exits `0` after printing a failed result.

- [ ] **Step 7: Map failed probe results to exit code 1**

Add the failure branch to `llm_probe` in `src/coding_agent/cli.py`:

```python
@llm_app.command("probe")
def llm_probe() -> None:
    result = probe_real_llm(RealLLMProvider.from_env())
    typer.echo(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    if not result.ok:
        raise typer.Exit(code=1)
```

- [ ] **Step 8: Run the disabled-command test and verify GREEN**

Run:

```powershell
pytest tests/test_cli.py::test_llm_probe_command_exits_one_when_disabled -v
```

Expected: `1 passed`.

- [ ] **Step 9: Run all CLI and probe tests**

Run:

```powershell
pytest tests/test_llm_probe.py tests/test_cli.py -v
```

Expected: all tests pass, including the existing Mock demo and credential status tests.

- [ ] **Step 10: Commit the CLI command**

```powershell
git add src/coding_agent/cli.py tests/test_cli.py
git commit -m "feat: expose real llm probe command"
```

---

### Task 5: Operator Documentation And Full Verification

**Files:**
- Modify: `README.md`
- Modify: `AGENT_LOG.md`

**Interfaces:**
- Consumes: the completed `llm probe` command and Docker Compose environment flow.
- Produces: reproducible operator instructions and final verification evidence.

- [ ] **Step 1: Document the probe without documenting a real key**

Add a `真实 LLM 连通性验证` section to `README.md` after the Docker startup instructions:

````markdown
## 真实 LLM 连通性验证

在 `.env` 中配置 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`，并设置：

```env
ENABLE_REAL_LLM=true
```

重新构建容器后执行一次安全探测：

```bash
docker compose up --build -d
docker compose exec coding-agent python -m coding_agent llm probe
```

探测只发送固定的低 token 请求并验证严格 Action Protocol，不会创建 Agent
运行、执行工具或修改工作区。输出不会包含 API Key 或模型原始响应。Mock 演示仍使用：

```bash
docker compose exec coding-agent python -m coding_agent demo bugfix
docker compose exec coding-agent python -m coding_agent demo dangerous-action
```
````

Append this entry to `AGENT_LOG.md` after all checks and the real probe succeed:

```markdown
## 2026-07-10 - Real LLM Probe

- Spec: `docs/superpowers/specs/2026-07-10-real-llm-probe-design.md`.
- Added the TDD-built `python -m coding_agent llm probe` command.
- The probe validates one strict `final` Action without constructing an Agent Loop or executing tools.
- Automated verification: backend tests, frontend tests/build, and Docker build passed.
- Mock verification: bugfix succeeded; dangerous-action was blocked as designed.
- Sanitized real-provider verification: `ok=true`, `model=glm-5.2`, `protocol_valid=true`, `action_kind=final`.
- Secret hygiene: no API key, Authorization header, or raw model response was added to Git.
```

- [ ] **Step 2: Run formatting and backend regression checks**

Run:

```powershell
pytest -q
```

Expected: all backend tests pass with zero failures.

- [ ] **Step 3: Verify the existing frontend remains buildable**

Run from `frontend`:

```powershell
npm run test -- run
npm run build
```

Expected: all frontend tests pass and Vite build exits `0`.

- [ ] **Step 4: Rebuild the Docker image**

Run:

```powershell
docker compose build
docker compose up -d
docker compose ps
```

Expected: image build exits `0` and the `coding-agent` service reports `Up`.

- [ ] **Step 5: Verify the Mock path remains deterministic**

Run:

```powershell
docker compose exec coding-agent python -m coding_agent demo bugfix
```

Expected: exit code `0` and status `succeeded`.

Run:

```powershell
docker compose exec coding-agent python -m coding_agent demo dangerous-action
```

Expected: exit code `1` with `guardrail_blocked`; this is the intended guardrail result.

- [ ] **Step 6: Perform the explicit real-provider probe**

Run only after automated tests and Docker build pass:

```powershell
docker compose exec coding-agent python -m coding_agent llm probe
```

Expected successful JSON fields:

```json
{
  "ok": true,
  "provider": "openai-compatible",
  "base_url": "https://njusehub.info/v1",
  "model": "glm-5.2",
  "protocol_valid": true,
  "action_kind": "final",
  "error_code": null
}
```

The output also contains a nonnegative `latency_ms` and a sanitized success
message. If it fails, use `error_code` to correct configuration or provider
compatibility before proceeding to WebUI Real Agent work.

- [ ] **Step 7: Check the final diff and secret hygiene**

Run:

```powershell
git diff --check
git status --short
git diff -- . ':!.env'
```

Expected: no whitespace errors, `.env` absent from Git status/diff, and only
the planned source, tests, and documentation changes present.

- [ ] **Step 8: Commit documentation and verification evidence**

```powershell
git add README.md AGENT_LOG.md
git commit -m "docs: document real llm probe workflow"
```

---

## Completion Gate

This increment is complete only when all of the following are true:

- [ ] Probe tests were observed failing before each production behavior was added.
- [ ] `pytest -q` reports zero failures.
- [ ] Frontend tests and build pass.
- [ ] Docker image rebuild succeeds.
- [ ] Mock bugfix succeeds and Mock dangerous-action is guardrail-blocked.
- [ ] The explicit real probe returns `ok: true` and `action_kind: "final"`.
- [ ] No API key or raw model response appears in Git-tracked files or terminal evidence.
