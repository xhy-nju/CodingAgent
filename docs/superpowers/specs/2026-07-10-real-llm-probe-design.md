# Real LLM Probe Design

## 1. Goal

Add a safe, repeatable command that proves the configured OpenAI-compatible
provider can be reached and can return one valid CodingAgent action:

```text
python -m coding_agent llm probe
```

The probe is the first increment toward the approved dual-mode WebUI. It must
validate the Base URL, API key, model identifier, response envelope, and strict
Action Protocol without executing any CodingAgent tool.

## 2. Scope

This increment includes:

- a reusable Real LLM probe service;
- a structured probe result;
- the `llm probe` CLI command;
- stable error classification and nonzero failure exit codes;
- automated tests that never contact the real provider;
- operator documentation for running the probe through Docker Compose.

This increment does not include:

- a browser-accessible probe endpoint;
- administrator login or sessions;
- choosing Mock or Real mode for an Agent run;
- a custom-task WebUI;
- any file, command, memory, or approval tool execution.

Those capabilities follow only after this isolated connectivity check is
working, so a real-model endpoint is not exposed before authentication exists.

## 3. Current Context

`RealLLMProvider` already reads `OPENAI_API_KEY`, `OPENAI_BASE_URL`,
`OPENAI_MODEL`, and `ENABLE_REAL_LLM` from the environment and sends an
OpenAI-compatible `POST /chat/completions` request. `parse_action` already
validates the strict CodingAgent Action schema. The CLI currently exposes
deterministic Mock demos and credential status, but it has no command that
actually contacts the configured provider.

Docker Compose supplies the project's ignored `.env` values to the container.
The Python process does not need to parse `.env` itself for the supported Docker
workflow.

## 4. Architecture

### 4.1 Probe service

Create `src/coding_agent/llm_probe.py` with one focused operation:

```python
def probe_real_llm(provider: RealLLMProvider) -> LLMProbeResult:
    ...
```

The service sends a fixed, low-token task through `provider.next_action()`.
The task asks for a `final` action with empty `args` and all required Action
Protocol fields. The returned text is passed to `parse_action`.

The probe succeeds only when:

1. the HTTP request succeeds;
2. the OpenAI-compatible response contains assistant content;
3. the content parses as exactly one strict CodingAgent action;
4. the action has `kind="final"`.

The service never constructs a dispatcher or `AgentLoop`, so even a malicious
or unexpected model response cannot execute a tool.

### 4.2 Structured result

Define `LLMProbeResult` in `llm_probe.py` as a Pydantic model with these fields:

```text
ok: bool
provider: str
base_url: str
model: str
latency_ms: int
protocol_valid: bool
action_kind: str | None
error_code: str | None
message: str
```

The result deliberately excludes the provider token and raw assistant content.
The CLI serializes this object as JSON, making the output both human-readable
and usable as verification evidence.

### 4.3 CLI command

Add an `llm` Typer command group and a `probe` command:

```text
python -m coding_agent llm probe
```

The command builds `RealLLMProvider.from_env()`, invokes
`probe_real_llm(provider)`, prints the result as JSON, and exits with:

- code `0` when `ok` is true;
- code `1` for configuration, network, HTTP, response, or protocol failures.

No command option accepts an API key. Credentials continue to come only from
the server-side environment.

## 5. Request And Data Flow

```text
operator
  -> CLI `llm probe`
  -> RealLLMProvider.from_env()
  -> fixed low-token chat completion request
  -> configured `/chat/completions`
  -> assistant content
  -> strict Action Parser
  -> sanitized LLMProbeResult JSON
```

The probe does not write to SQLite, the audit event stream, memory, or a demo
workspace. Its only external effect is one chat-completion request.

## 6. Error Handling

Failures are converted to a sanitized result rather than an uncaught traceback:

| Error code | Condition | Operator action |
| --- | --- | --- |
| `real_llm_disabled` | `ENABLE_REAL_LLM` is not true | Enable the explicit gate |
| `api_key_missing` | `OPENAI_API_KEY` is empty | Configure the server-side key |
| `authentication_failed` | Provider returns HTTP 401 or 403 | Check key validity and account access |
| `model_or_endpoint_not_found` | Provider returns HTTP 404 | Check Base URL and model identifier |
| `provider_rejected_request` | Other HTTP 4xx response | Check provider compatibility and model request rules |
| `provider_unavailable` | HTTP 5xx response | Retry after the provider recovers |
| `request_timeout` | Request exceeds the configured timeout | Check network/provider latency and retry |
| `network_error` | DNS, TLS, connection, or other transport failure | Check host and network access |
| `invalid_provider_response` | Response envelope has no assistant content | Check OpenAI compatibility |
| `protocol_error` | Assistant content is not one valid `final` action | Check model behavior or prompt compatibility |

Error messages must not contain the API key, authorization header, or raw
provider response body. The provider's status code may be included because it
is useful and not secret.

## 7. Security Properties

- The API key remains in the container environment and Authorization header.
- Probe output never contains the API key or Authorization header.
- Raw model output is not printed or stored.
- No browser endpoint is introduced before administrator authentication.
- No CodingAgent tool can run during a probe.
- Mock demos remain independent of all real-provider settings.
- Disabling `ENABLE_REAL_LLM` immediately blocks future probes.

## 8. Testing Strategy

Tests use fakes or monkeypatching at the provider boundary; they do not use the
network or the user's API key.

`tests/test_llm_probe.py` covers:

- a valid `final` action produces a successful sanitized result;
- a valid non-`final` action is rejected as `protocol_error`;
- malformed model content is rejected as `protocol_error`;
- disabled and missing-key configuration errors are classified;
- authentication, not-found, server, timeout, network, and malformed-envelope
  failures are classified without leaking secrets.

`tests/test_cli.py` covers:

- `llm probe` prints JSON and exits `0` for success;
- `llm probe` prints sanitized JSON and exits `1` for failure;
- probe output never includes the configured test token.

Existing provider, CLI, Mock demo, API, and full test suites must continue to
pass. The Docker image must rebuild after the change.

## 9. Operator Workflow

After implementation and automated verification, the operator runs:

```powershell
docker compose up --build -d
docker compose exec coding-agent python -m coding_agent llm probe
```

The second command performs exactly one real chat-completion request. A success
result reports `ok: true`, `protocol_valid: true`, and `action_kind: "final"`
without exposing credentials.

## 10. Acceptance Criteria

- The command performs one real provider request when explicitly invoked.
- A valid strict `final` action returns exit code `0` and sanitized JSON.
- Every defined failure returns exit code `1` and a stable error code.
- No API key or raw model content appears in output, exceptions, tests, or Git.
- The probe cannot execute tools or modify a CodingAgent workspace.
- Mock demos still work when real LLM access is enabled, disabled, or broken.
- Automated tests and the Docker build pass before the real probe is attempted.

