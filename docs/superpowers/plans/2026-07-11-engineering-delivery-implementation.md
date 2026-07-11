# CodingAgent Engineering Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete a production-ready course deliverable in which anonymous users can run deterministic Mock demos while authenticated administrators can run the same guarded AgentLoop with a real OpenAI-compatible model.

**Architecture:** Keep FastAPI, React, SQLite, and the existing AgentLoop in one deployable service. Add focused credential, authentication, run orchestration, and API authorization modules; use a bounded in-process executor for real runs and persisted SQLite events for live SSE. Preserve a single execution path through Action parsing, Guardrails, tools, feedback, Memory, HITL, and audit storage.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic 2, Typer, httpx, keyring, SQLite, React 18, TypeScript, Vite, Vitest, Docker Compose, Nginx, GitHub Actions, GHCR.

## Global Constraints

- Real LLM defaults remain `https://njusehub.info/v1` and `glm-5.2`.
- Mock demos remain deterministic and anonymously accessible.
- Real runs, approvals, Memory, and management operations require an administrator session.
- API keys never enter browser state, API responses, logs, events, SQLite, prompts, or committed files.
- Real and Mock modes use the same AgentLoop, Action parser, Guardrails, tools, feedback, Memory, HITL, and EventBus.
- Real runs can operate only on copied sample workspaces under `CODING_AGENT_DATA_DIR`.
- CI never calls a real model endpoint.
- Production deployment rejects default administrator and session secrets.
- Every task follows red-green-refactor and ends with a focused commit.

## File Responsibility Map

- `src/coding_agent/credentials.py`: credential source resolution and Keyring lifecycle.
- `src/coding_agent/auth.py`: signed administrator sessions and request authorization helpers.
- `src/coding_agent/run_service.py`: workspace creation, loop construction, bounded background execution, restart recovery.
- `src/coding_agent/llm.py`: real provider prompt and OpenAI-compatible transport.
- `src/coding_agent/agent_loop.py`: pre-created run continuation and terminal failure recording.
- `src/coding_agent/store.py`: persisted run status, listing, event cursor, and interrupted-run recovery.
- `src/coding_agent/api.py`: HTTP schemas, route wiring, access matrix, SSE transport.
- `src/coding_agent/cli.py`: hidden credential lifecycle commands and real probe UX.
- `frontend/src/api.ts`: typed auth, run, approval, Memory, and status API client.
- `frontend/src/types.ts`: shared frontend response types.
- `frontend/src/App.tsx`: operational console workflows and UI state.
- `frontend/src/styles.css`: responsive console, dialog, forms, and stable control dimensions.
- `deploy/nginx.conf`: HTTPS reverse proxy template.
- `docker-compose.yml`: local source-build deployment.
- `docker-compose.production.yml`: published-image deployment with Docker Secret.
- `.github/workflows/ci.yml`: verification pipeline.
- `.github/workflows/publish-image.yml`: GHCR image publication.

---

### Task 1: Secure Credential Lifecycle

**Files:**
- Modify: `src/coding_agent/credentials.py`
- Modify: `src/coding_agent/llm.py`
- Modify: `src/coding_agent/llm_probe.py`
- Modify: `src/coding_agent/cli.py`
- Test: `tests/test_credentials_llm.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: environment variables `OPENAI_API_KEY_FILE`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, and `ENABLE_REAL_LLM`.
- Produces: `CredentialSnapshot`, `CredentialService.resolve()`, `CredentialService.set_keyring_token()`, `CredentialService.clear_keyring_token()`, and `RealLLMProvider.from_credentials(snapshot)`.

- [ ] **Step 1: Write failing source-priority and lifecycle tests**

Add tests that inject a fake Keyring adapter and a temporary Docker Secret:

```python
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


def test_credential_priority_prefers_secret_file(tmp_path, monkeypatch) -> None:
    secret = tmp_path / "openai_api_key"
    secret.write_text("file-token\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY_FILE", str(secret))
    monkeypatch.setenv("OPENAI_API_KEY", "environment-token")
    service = CredentialService(keyring_backend=FakeKeyring("keyring-token"))

    snapshot = service.resolve()

    assert snapshot.provider_token == "file-token"
    assert snapshot.source == "docker-secret"


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
```

- [ ] **Step 2: Run the new credential tests and verify red**

Run: `pytest tests/test_credentials_llm.py -v`

Expected: FAIL because `CredentialSnapshot`, constructor injection, and lifecycle methods do not exist.

- [ ] **Step 3: Implement the credential snapshot and source resolver**

Implement these exact public shapes:

```python
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
        token = self.keyring_backend.get_password(self.SERVICE_NAME, self.USERNAME)
        return self._snapshot(token.strip() if token else None, "keyring" if token else "missing")

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

    def status(self) -> dict[str, object]:
        snapshot = self.resolve()
        return {
            "provider": "openai-compatible",
            "configured": snapshot.configured,
            "source": snapshot.source,
            "base_url": snapshot.base_url,
            "model": snapshot.model,
            "real_enabled": snapshot.real_enabled,
        }
```

`resolve()` must reject secret files larger than 16 KiB, reject empty tokens, and use file, environment, then Keyring precedence. `status()` must omit `provider_token` entirely.

- [ ] **Step 4: Add hidden CLI set, update, status, and clear commands**

Use `typer.prompt("API key", hide_input=True, confirmation_prompt=True)` for set/update. Clear must print whether a Keyring value was removed and explain that environment and Docker Secret sources are unaffected. Refactor `RealLLMProvider` and `llm probe` to consume the same snapshot.

- [ ] **Step 5: Verify focused and compatibility tests**

Run: `pytest tests/test_credentials_llm.py tests/test_cli.py tests/test_distribution.py -v`

Expected: all selected tests PASS and no output contains a configured fake token.

- [ ] **Step 6: Commit Task 1**

```bash
git add src/coding_agent/credentials.py src/coding_agent/llm.py src/coding_agent/llm_probe.py src/coding_agent/cli.py tests/test_credentials_llm.py tests/test_cli.py
git commit -m "feat: add secure credential lifecycle"
```

### Task 2: Signed Administrator Sessions

**Files:**
- Create: `src/coding_agent/auth.py`
- Modify: `src/coding_agent/api.py`
- Create: `tests/test_auth.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: `ADMIN_PASSWORD`, `SESSION_SECRET`, `COOKIE_SECURE`, request Cookie and Origin headers.
- Produces: `AuthService.issue_session()`, `AuthService.verify_session()`, `require_admin(request)`, and `/api/auth/login|status|logout`.

- [ ] **Step 1: Write failing session unit tests**

```python
def test_signed_session_round_trip() -> None:
    auth = AuthService("admin-password", "session-secret-at-least-32-bytes", ttl_seconds=3600)
    token = auth.issue_session(now=100)

    session = auth.verify_session(token, now=101)

    assert session.authenticated is True
    assert session.expires_at == 3700


def test_tampered_and_expired_sessions_are_rejected() -> None:
    auth = AuthService("admin-password", "session-secret-at-least-32-bytes", ttl_seconds=10)
    token = auth.issue_session(now=100)
    assert auth.verify_session(token + "x", now=101).authenticated is False
    assert auth.verify_session(token, now=111).authenticated is False
```

- [ ] **Step 2: Run auth tests and verify red**

Run: `pytest tests/test_auth.py -v`

Expected: FAIL with import error for `coding_agent.auth`.

- [ ] **Step 3: Implement HMAC session service**

Define `SessionStatus(authenticated: bool, expires_at: int | None)` and sign a URL-safe base64 JSON payload containing `issued_at`, `expires_at`, and a random `session_id` with HMAC-SHA256. Verify signatures using `hmac.compare_digest`. Never store the administrator password in the token.

- [ ] **Step 4: Add auth routes and Cookie behavior tests**

```python
def test_login_sets_http_only_same_site_cookie(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "correct-password")
    monkeypatch.setenv("SESSION_SECRET", "session-secret-that-is-long-enough")
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post("/api/auth/login", json={"password": "correct-password"})

    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert response.json()["authenticated"] is True
```

Add uniform 401 tests for wrong password and unsigned Cookie. Add authenticated status and logout tests.

- [ ] **Step 5: Protect approvals and Memory and verify the access matrix**

`GET /api/approvals`, `POST /api/approvals/{id}/decision`, and `GET /api/memory` must return 401 without a valid session. Mock demo creation and policy listing must remain 200 anonymously.

Run: `pytest tests/test_auth.py tests/test_api.py -v`

Expected: all selected tests PASS.

- [ ] **Step 6: Commit Task 2**

```bash
git add src/coding_agent/auth.py src/coding_agent/api.py tests/test_auth.py tests/test_api.py
git commit -m "feat: protect admin operations with signed sessions"
```

### Task 3: Persisted Run Lifecycle And Recovery

**Files:**
- Modify: `src/coding_agent/store.py`
- Modify: `src/coding_agent/agent_loop.py`
- Modify: `src/coding_agent/events.py`
- Test: `tests/test_store_events.py`
- Test: `tests/test_agent_loop.py`

**Interfaces:**
- Consumes: persisted `runs` and ordered `events` tables.
- Produces: `SqliteStore.list_events_after()`, `SqliteStore.list_runs_by_status()`, `SqliteStore.fail_interrupted_runs()`, `AgentLoop.start_run()`, and `AgentLoop.continue_run()`.

- [ ] **Step 1: Write failing cursor and recovery tests**

```python
def test_list_events_after_uses_sequence_cursor(tmp_path) -> None:
    store = SqliteStore(tmp_path / "agent.db")
    run_id = store.create_run("task", str(tmp_path), "strict_demo", "mock")
    store.append_event(run_id, "run.started", {"n": 1})
    first = store.list_events_after(run_id, after_sequence=0)
    store.append_event(run_id, "run.finished", {"n": 2})

    second = store.list_events_after(run_id, after_sequence=first[-1]["sequence"])

    assert [event["payload"]["n"] for event in second] == [2]


def test_fail_interrupted_runs_only_changes_created_and_running(tmp_path) -> None:
    store = SqliteStore(tmp_path / "agent.db")
    running = store.create_run("one", str(tmp_path), "strict_demo", "real")
    waiting = store.create_run("two", str(tmp_path), "strict_demo", "real")
    store.update_run_status(running, RunStatus.RUNNING)
    store.update_run_status(waiting, RunStatus.WAITING_APPROVAL)

    changed = store.fail_interrupted_runs()

    assert changed == [running]
    assert store.get_run(waiting)["status"] == "waiting_approval"
```

- [ ] **Step 2: Run lifecycle tests and verify red**

Run: `pytest tests/test_store_events.py tests/test_agent_loop.py -v`

Expected: FAIL because cursor and recovery methods do not exist.

- [ ] **Step 3: Implement cursor reads, terminal timestamps, and recovery**

`list_events_after(run_id, after_sequence, limit=100)` must return ordered records including `sequence`. `update_run_status()` must set `finished_at` for terminal statuses. `fail_interrupted_runs()` must atomically fail `created` and `running` rows and append a sanitized interruption event for each run.

- [ ] **Step 4: Refactor AgentLoop to support pre-created runs**

Keep `run(task)` backward compatible. Add:

```python
def start_run(self, task: str) -> str:
    run_id = self.store.create_run(task, str(self.workspace), self.policy_profile, self.llm_mode)
    self.store.update_run_status(run_id, RunStatus.RUNNING)
    self.events.append_event(run_id, EventType.RUN_STARTED, {"task": task})
    return run_id

def continue_run(self, run_id: str) -> RunSummary:
    run = self.store.get_run(run_id)
    return self._continue(run_id, str(run["task"]), start_step=0, feedback=[])

def fail_run(self, run_id: str, reason: str) -> RunSummary:
    feedback = FeedbackSignal(
        type=FeedbackType.COMMAND_FAILED,
        severity="error",
        summary=reason,
        details={},
    )
    self.events.append_event(
        run_id, EventType.FEEDBACK_RECORDED, feedback.model_dump(mode="json")
    )
    self.store.update_run_status(run_id, RunStatus.FAILED)
    self.events.append_event(run_id, EventType.RUN_FINISHED, {"status": "failed"})
    return RunSummary(run_id=run_id, status="failed", feedback=[feedback])
```

`run(task)` becomes `run_id = start_run(task); return continue_run(run_id)`. Catching transport exceptions remains the orchestration layer's responsibility.

- [ ] **Step 5: Verify lifecycle regression suite**

Run: `pytest tests/test_store_events.py tests/test_agent_loop.py tests/test_approvals.py -v`

Expected: all selected tests PASS and existing Mock summaries remain unchanged.

- [ ] **Step 6: Commit Task 3**

```bash
git add src/coding_agent/store.py src/coding_agent/agent_loop.py src/coding_agent/events.py tests/test_store_events.py tests/test_agent_loop.py
git commit -m "feat: persist resumable run lifecycle"
```

### Task 4: Real Agent Orchestration

**Files:**
- Create: `src/coding_agent/run_service.py`
- Modify: `src/coding_agent/llm.py`
- Modify: `src/coding_agent/api.py`
- Create: `tests/test_run_service.py`
- Modify: `tests/test_credentials_llm.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: `CredentialSnapshot`, `AgentLoop.start_run()`, `AgentLoop.continue_run()`, the strict demo policy, and copied sample workspace.
- Produces: `RunService.create_mock_run()`, `RunService.create_real_run()`, `RunService.get_summary()`, `POST /api/runs`, and `GET /api/runs/{run_id}`.

- [ ] **Step 1: Write a failing real-run integration test with a fake provider**

```python
def action(tool: str, args: dict[str, object]) -> str:
    return json.dumps({
        "kind": "tool",
        "tool": tool,
        "args": args,
        "reason": "test action",
        "expectation": "test result",
    })


class ScriptedProvider(LLMProvider):
    def __init__(self, actions: list[str]) -> None:
        self.actions = iter(actions)

    def next_action(self, context: LLMContext) -> str:
        return next(self.actions)


def test_real_run_uses_guarded_agent_loop(tmp_path) -> None:
    provider = ScriptedProvider([
        action("run_tests", {"target": "."}),
        action("write_file", {"path": "calculator.py", "content": "def add(a, b):\n    return a + b\n"}),
        action("run_tests", {"target": "."}),
    ])
    service = RunService(data_dir=tmp_path, real_provider_factory=lambda: provider)

    run_id = service.create_real_run("Repair the calculator", background=False)
    summary = service.get_summary(run_id)

    assert summary.status == "succeeded"
    assert SqliteStore(tmp_path / "agent.db").get_run(run_id)["llm_mode"] == "real"
```

- [ ] **Step 2: Run orchestration tests and verify red**

Run: `pytest tests/test_run_service.py -v`

Expected: FAIL with import error for `coding_agent.run_service`.

- [ ] **Step 3: Implement RunService and bounded execution**

Use `ThreadPoolExecutor(max_workers=int(os.getenv("REAL_RUN_WORKERS", "2")))`. `create_real_run(task, background=True)` validates task length 1 to 4000 characters, copies `demos/sample_workspace`, builds the same dispatcher and policy as Mock, starts a persisted run, and submits continuation. The worker catches every exception, redacts it, calls `loop.fail_run()`, and never re-raises into the executor.

- [ ] **Step 4: Expand the real provider prompt and transport errors**

The system message must include the exact JSON Action fields, allowed tools `read_file`, `write_file`, `run_tests`, `run_lint`, `run_command`, and `memory_write`, plus the workspace and one-action constraints. Include structured feedback and Memory in the user message. Convert `httpx.TimeoutException`, `httpx.HTTPStatusError`, missing choices, and empty content into stable provider exceptions without response bodies or authorization headers.

- [ ] **Step 5: Add authenticated real-run API tests**

Test 401 without login, 503 when disabled or unconfigured, 202 with `run_id` when ready, and 200 from the status endpoint. Inject a fake RunService into `create_app()` so API tests do not call the network.

Run: `pytest tests/test_run_service.py tests/test_credentials_llm.py tests/test_api.py -v`

Expected: all selected tests PASS.

- [ ] **Step 6: Commit Task 4**

```bash
git add src/coding_agent/run_service.py src/coding_agent/llm.py src/coding_agent/api.py tests/test_run_service.py tests/test_credentials_llm.py tests/test_api.py
git commit -m "feat: run real models through guarded agent loop"
```

### Task 5: Live SSE And Durable HITL Resume

**Files:**
- Modify: `src/coding_agent/run_service.py`
- Modify: `src/coding_agent/api.py`
- Modify: `src/coding_agent/approvals.py`
- Modify: `tests/test_api.py`
- Modify: `tests/test_approvals.py`

**Interfaces:**
- Consumes: event sequence cursor, persisted approval Action and run metadata.
- Produces: live `/api/runs/{run_id}/events?after=`, `RunService.resolve_approval()`, and durable exactly-once decisions.

- [ ] **Step 1: Write failing live SSE and authorization tests**

Create one Mock run and one Real run. Assert an anonymous request can read Mock events, an anonymous request receives 401 for Real events, and an authenticated request receives ordered `id: <sequence>` SSE fields. Add a test where an event is appended after the streaming response starts and is received before terminal closure.

- [ ] **Step 2: Run API tests and verify red**

Run: `pytest tests/test_api.py -v`

Expected: FAIL because SSE currently snapshots events once and does not authorize by persisted mode.

- [ ] **Step 3: Implement live cursor streaming**

Poll `list_events_after()` every 250 ms, emit `id`, mapped public `event`, and redacted JSON `data`. Stop after a terminal run has no remaining events. Emit a 15-second comment heartbeat while idle. Reject access to Real events before creating the StreamingResponse.

- [ ] **Step 4: Rebuild approval execution context from storage**

Replace the in-memory `pending_loops` requirement with `RunService.resolve_approval()`. Rebuild Guardrail, dispatcher, Memory, and LLM provider from persisted run metadata and workspace. `ApprovalService.approve_once()` and `record_execution()` remain the transaction gates so a second approval cannot execute again.

- [ ] **Step 5: Verify SSE and exactly-once approval behavior**

Run: `pytest tests/test_api.py tests/test_approvals.py tests/test_agent_loop.py -v`

Expected: all selected tests PASS, including duplicate approval returning 409 with one recorded tool execution.

- [ ] **Step 6: Commit Task 5**

```bash
git add src/coding_agent/run_service.py src/coding_agent/api.py src/coding_agent/approvals.py tests/test_api.py tests/test_approvals.py
git commit -m "feat: stream live runs and resume durable approvals"
```

### Task 6: Complete Operational WebUI

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: auth, run creation/status/events, approvals, Memory, policies, and credential status endpoints.
- Produces: anonymous Mock workflow and authenticated Real, approval, Memory, and session workflows.

- [ ] **Step 1: Add failing frontend workflow tests**

```tsx
it("requires login before starting a real run", async () => {
  render(<App />);
  await userEvent.click(await screen.findByRole("button", { name: "Real" }));
  await userEvent.click(screen.getByRole("button", { name: /Start real run/i }));
  expect(screen.getByRole("dialog", { name: /Administrator login/i })).toBeInTheDocument();
});

it("submits an approval with reviewer and reason", async () => {
  vi.mocked(fetchAuthStatus).mockResolvedValue({ authenticated: true, expires_at: 4102444800 });
  vi.mocked(fetchApprovals).mockResolvedValue({
    approvals: [{
      id: "approval-1",
      run_id: "run-1",
      action_id: "action-1",
      action: {
        kind: "tool",
        tool: "run_command",
        args: { command: "git status" },
        reason: "inspect repository",
        expectation: "working tree status",
      },
      state: "pending",
      rules: ["command_requires_approval"],
      reason: "Manual review required",
      step_index: 1,
    }],
  });
  vi.mocked(decideApproval).mockResolvedValue({
    approval_id: "approval-1",
    state: "approved_once",
    run: { run_id: "run-1", status: "succeeded", feedback: [] },
  });
  render(<App />);
  await userEvent.click(await screen.findByRole("button", { name: /Approvals/i }));
  await userEvent.type(screen.getByLabelText("Reviewer"), "course-admin");
  await userEvent.type(screen.getByLabelText("Reason"), "Reviewed command and workspace");
  await userEvent.click(screen.getByRole("button", { name: "Approve once" }));
  expect(await screen.findByText("approved_once")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run frontend tests and verify red**

Run: `cd frontend && npm test`

Expected: FAIL because mode selection, auth dialog, and approval controls do not exist.

- [ ] **Step 3: Implement typed clients and state models**

Add `AuthStatus`, `RunMode`, `RunRecord`, `ApprovalDecision`, and `ApiError`. `jsonRequest()` must parse server `detail`, include `credentials: "same-origin"`, and throw `ApiError(status, detail)`. Add typed login, logout, create Real run, fetch run, decide approval, and filtered Memory functions.

- [ ] **Step 4: Implement the complete console workflows**

Add a stable Mock/Real segmented control, real task text area, login dialog, logout button, live run status polling, ordered event timeline, approval reviewer/reason form, Memory query/tags controls, and credential configuration guidance. Keep Mock buttons anonymous. Disable pending actions and display inline API errors without exposing server internals.

- [ ] **Step 5: Complete responsive styling and frontend verification**

Use existing colors and 6 to 8 px radii. Keep forms unframed inside existing panels, use Lucide icons, set stable button/input heights, and add mobile rules at 760 px without overlapping navigation or dialogs.

Run: `cd frontend && npm test`

Expected: all frontend tests PASS.

Run: `cd frontend && npm run build`

Expected: TypeScript and Vite build PASS.

- [ ] **Step 6: Commit Task 6**

```bash
git add frontend/src/types.ts frontend/src/api.ts frontend/src/App.tsx frontend/src/styles.css frontend/src/App.test.tsx
git commit -m "feat: complete mock and real web console"
```

### Task 7: Production Distribution, CI, And Public Image

**Files:**
- Modify: `.env.example`
- Modify: `Dockerfile`
- Modify: `docker-compose.yml`
- Create: `docker-compose.production.yml`
- Create: `deploy/nginx.conf`
- Modify: `.github/workflows/ci.yml`
- Create: `.github/workflows/publish-image.yml`
- Modify: `tests/test_distribution.py`

**Interfaces:**
- Consumes: GHCR repository metadata and server-side Docker Secret.
- Produces: healthy source-build Compose service, production pull-based Compose service, Nginx template, CI gates, and GHCR publication workflow.

- [ ] **Step 1: Write failing distribution assertions**

Extend `tests/test_distribution.py` to assert:

```python
assert "OPENAI_API_KEY_FILE" in production_compose
assert "/run/secrets/openai_api_key" in production_compose
assert "healthcheck:" in production_compose
assert "ghcr.io/${GITHUB_REPOSITORY_OWNER}/coding-agent" in production_compose
assert "packages: write" in publish_workflow
assert "docker/build-push-action" in publish_workflow
assert "proxy_set_header X-Forwarded-Proto" in nginx_config
```

- [ ] **Step 2: Run distribution tests and verify red**

Run: `pytest tests/test_distribution.py -v`

Expected: FAIL because production Compose, Nginx, and publication workflow do not exist.

- [ ] **Step 3: Add production deployment files**

Production Compose must use the GHCR image, mount `./secrets/openai_api_key` read-only at `/run/secrets/openai_api_key`, set `OPENAI_API_KEY_FILE`, require `ADMIN_PASSWORD` and `SESSION_SECRET`, enable `COOKIE_SECURE`, persist `/data`, and expose only `127.0.0.1:8000:8000`. Health check calls `/api/health`.

Nginx must proxy to `127.0.0.1:8000`, forward Host, real IP, scheme, cookies, and disable response buffering for `/api/runs/` SSE paths. TLS certificate paths use `/etc/letsencrypt/live/example.com/` and README commands explain replacing the hostname.

- [ ] **Step 4: Add CI and GHCR workflows**

CI runs `pytest -q`, `npm test`, `npm run build`, `docker build`, `docker compose config --quiet`, and a tracked-file secret pattern scan. The publish workflow runs on `v*` tags and manual dispatch, logs into GHCR using `GITHUB_TOKEN`, builds the Dockerfile, and pushes semver and `latest` tags.

- [ ] **Step 5: Verify all distribution artifacts locally**

Run: `pytest tests/test_distribution.py -v`

Expected: PASS.

Run: `docker compose config --quiet`

Expected: exit code 0.

Run: `docker compose build`

Expected: image builds successfully and retains the non-root runtime user.

- [ ] **Step 6: Commit Task 7**

```bash
git add .env.example Dockerfile docker-compose.yml docker-compose.production.yml deploy/nginx.conf .github/workflows/ci.yml .github/workflows/publish-image.yml tests/test_distribution.py
git commit -m "chore: complete secure production distribution"
```

### Task 8: Course Documents And Final Engineering Verification

**Files:**
- Modify: `README.md`
- Modify: `SPEC.md`
- Modify: `PLAN.md`
- Modify: `SPEC_PROCESS.md`
- Modify: `AGENT_LOG.md`
- Modify: `REFLECTION.md`
- Create: `docs/deployment-aliyun.md`

**Interfaces:**
- Consumes: verified commands and actual commit hashes from Tasks 1 through 7.
- Produces: reproducible Chinese delivery documentation and an evidence checklist ready for publication.

- [ ] **Step 1: Update the Chinese project and deployment documentation**

README must include project purpose, four main contribution dimensions, directory tree, Mock workflow, Real workflow, credential set/status/update/clear commands, `.env` plaintext risk, Docker Secret deployment, known limitations, public image placeholder policy, and public URL placeholder policy. Use explicit text stating that real values are recorded only after successful publication.

`docs/deployment-aliyun.md` must include Ubuntu Docker prerequisites, security group ports 80/443, secret file permissions, production Compose startup, Nginx installation, Certbot HTTPS, health check, logs, upgrade, rollback, and backup commands.

- [ ] **Step 2: Update specification and process evidence**

Mark the current SPEC version as implementation complete only after verification. Add Tasks 1 through 8 to PLAN and record each actual commit hash. Record design decisions, exact verification commands, observed counts, and human choices in SPEC_PROCESS and AGENT_LOG. Keep REFLECTION explicitly student-owned; add only a factual evidence appendix and AI assistance disclosure template.

- [ ] **Step 3: Run the complete automated verification suite**

Run: `pytest -q`

Expected: all backend tests PASS.

Run: `cd frontend && npm test`

Expected: all frontend tests PASS without unknown CLI option warnings.

Run: `cd frontend && npm run build`

Expected: build PASS.

Run: `docker compose config --quiet`

Expected: exit code 0.

Run: `docker compose build`

Expected: image build PASS.

- [ ] **Step 4: Run mechanism and real-provider acceptance**

Run: `python -m coding_agent demo bugfix`

Expected: exit code 0, status `succeeded`, and test-failure feedback before the corrective action.

Run: `python -m coding_agent demo dangerous-action`

Expected: exit code 1, status `failed`, and `guardrail_blocked` feedback.

Run when a real credential is intentionally configured: `python -m coding_agent llm probe`

Expected: exit code 0 and a non-empty model response summary with no token output.

- [ ] **Step 5: Perform browser verification**

Start the Docker service and verify desktop 1440 x 900 and mobile 390 x 844 views. Confirm anonymous Mock runs, login failure/success, Real mode readiness, run timeline, approval form, Memory filtering, logout, no text overflow, no overlapping controls, and no browser console errors.

- [ ] **Step 6: Commit Task 8**

```bash
git add README.md SPEC.md PLAN.md SPEC_PROCESS.md AGENT_LOG.md REFLECTION.md docs/deployment-aliyun.md
git commit -m "docs: complete engineering delivery evidence"
```

## Final Publication Gate

After Task 8 passes locally:

1. Push `task1-domain-models` to GitHub and open a pull request.
2. Wait for GitHub Actions to pass on the latest commit.
3. Merge through the pull request so the public history preserves the feature branch.
4. Tag the merged commit with a version such as `v1.0.0` and verify the GHCR package is public.
5. Deploy `docker-compose.production.yml` to the Aliyun Ubuntu host.
6. Verify the public HTTPS URL from outside the server.
7. Replace documentation publication markers with the actual PR, CI, image, and WebUI URLs in one final evidence commit.
