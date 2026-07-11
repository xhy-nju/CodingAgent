from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from coding_agent.agent_loop import AgentLoop
from coding_agent.approvals import ApprovalService
from coding_agent.auth import AuthService, SessionStatus
from coding_agent.credentials import CredentialService, CredentialSnapshot
from coding_agent.domain import ApprovalState, RunStatus
from coding_agent.events import EventBus
from coding_agent.guardrails import GuardrailEngine
from coding_agent.llm import MockLLMProvider
from coding_agent.memory import MemoryService
from coding_agent.policies import load_policy
from coding_agent.redaction import redact_value
from coding_agent.run_service import RealRunUnavailable, RunService
from coding_agent.store import SqliteStore
from coding_agent.tools.dispatcher import build_default_dispatcher


class DemoRequest(BaseModel):
    name: str


class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    reviewer: str
    reason: str


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=4096)


class CreateRunRequest(BaseModel):
    mode: Literal["real"]
    task: str = Field(min_length=1, max_length=4000)


def _workspace_for_demo(name: str, data_dir: Path) -> Path:
    demo_root = data_dir / "demo-workspaces"
    demo_root.mkdir(parents=True, exist_ok=True)

    if name == "dangerous-action":
        return Path(tempfile.mkdtemp(prefix="coding-agent-empty-", dir=demo_root))
    if name == "bugfix":
        tempdir = Path(tempfile.mkdtemp(prefix="coding-agent-demo-", dir=demo_root))
        shutil.copytree(Path("demos/sample_workspace"), tempdir / "workspace")
        return tempdir / "workspace"
    raise HTTPException(status_code=400, detail="unknown demo")


def _run_demo(
    name: str, data_dir: Path, credential_snapshot: CredentialSnapshot
) -> tuple[dict[str, Any], AgentLoop]:
    workspace = _workspace_for_demo(name, data_dir)
    store = SqliteStore(data_dir / "agent.db", credential_snapshot=credential_snapshot)
    policy = load_policy("strict_demo", Path("config/policies"))
    memory = MemoryService(store)
    dispatcher = build_default_dispatcher(
        GuardrailEngine(policy, workspace),
        workspace,
        policy,
        memory=memory,
    )
    script_name = "dangerous_action" if name == "dangerous-action" else "bugfix_with_feedback"
    loop = AgentLoop(
        store=store,
        events=EventBus(store),
        memory=memory,
        dispatcher=dispatcher,
        llm=MockLLMProvider(script_name=script_name),
        workspace=workspace,
        policy_profile="strict_demo",
        llm_mode="mock",
        max_steps=8,
    )
    return loop.run(f"demo {name}").model_dump(mode="json"), loop


def _frontend_dist_dir() -> Path:
    return Path(os.environ.get("CODING_AGENT_FRONTEND_DIST", "frontend/dist"))


def _mount_frontend(app: FastAPI) -> None:
    frontend_dist = _frontend_dist_dir()
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


def create_app(
    data_dir: Path | None = None,
    credential_service: CredentialService | None = None,
    auth_service: AuthService | None = None,
    run_service: RunService | None = None,
) -> FastAPI:
    app = FastAPI(title="CodingAgent Harness")
    app.state.pending_loops = {}
    runtime_dir = data_dir or Path(os.environ.get("CODING_AGENT_DATA_DIR", ".coding-agent-data"))
    credentials = credential_service or CredentialService()
    auth = auth_service or AuthService.from_env()

    def ensure_runtime_dir() -> Path:
        runtime_dir.mkdir(parents=True, exist_ok=True)
        return runtime_dir

    def current_snapshot() -> CredentialSnapshot:
        return credentials.resolve()

    def store(snapshot: CredentialSnapshot) -> SqliteStore:
        return SqliteStore(ensure_runtime_dir() / "agent.db", credential_snapshot=snapshot)

    def public(value: Any, snapshot: CredentialSnapshot) -> Any:
        return redact_value(value, snapshot.provider_token)[0]

    runs = run_service or RunService(
        data_dir=runtime_dir,
        credential_resolver=current_snapshot,
    )
    app.state.run_service = runs

    def session_status(request: Request) -> SessionStatus:
        return auth.verify_session(request.cookies.get(AuthService.COOKIE_NAME))

    def require_admin(request: Request) -> None:
        if not session_status(request).authenticated:
            raise HTTPException(status_code=401, detail="authentication required")

    def require_same_origin(request: Request) -> None:
        origin = request.headers.get("origin")
        expected = f"{request.url.scheme}://{request.url.netloc}"
        if origin and origin.rstrip("/") != expected.rstrip("/"):
            raise HTTPException(status_code=403, detail="cross-origin request denied")

    @app.post("/api/auth/login")
    def login(request: LoginRequest, response: Response) -> dict[str, object]:
        if not auth.verify_password(request.password):
            raise HTTPException(status_code=401, detail="invalid credentials")
        try:
            token = auth.issue_session()
        except RuntimeError as exc:
            raise HTTPException(status_code=401, detail="invalid credentials") from exc
        status = auth.verify_session(token)
        response.set_cookie(
            AuthService.COOKIE_NAME,
            token,
            max_age=auth.ttl_seconds,
            path="/",
            secure=auth.cookie_secure,
            httponly=True,
            samesite="strict",
        )
        return {
            "authenticated": status.authenticated,
            "expires_at": status.expires_at,
        }

    @app.get("/api/auth/status")
    def auth_status(request: Request) -> dict[str, object]:
        status = session_status(request)
        return {
            "authenticated": status.authenticated,
            "expires_at": status.expires_at,
        }

    @app.post("/api/auth/logout")
    def logout(request: Request, response: Response) -> dict[str, object]:
        require_same_origin(request)
        response.delete_cookie(
            AuthService.COOKIE_NAME,
            path="/",
            secure=auth.cookie_secure,
            httponly=True,
            samesite="strict",
        )
        return {"authenticated": False, "expires_at": None}

    @app.post("/api/runs/demo")
    def create_demo_run(request: DemoRequest) -> dict[str, Any]:
        snapshot = current_snapshot()
        result, loop = _run_demo(request.name, ensure_runtime_dir(), snapshot)
        if result["status"] == RunStatus.WAITING_APPROVAL.value:
            app.state.pending_loops[result["run_id"]] = loop
        return public(result, snapshot)

    @app.post("/api/runs", status_code=202)
    def create_run(request: CreateRunRequest, http_request: Request) -> dict[str, object]:
        require_admin(http_request)
        require_same_origin(http_request)
        try:
            run_id = runs.create_real_run(request.task, background=True)
        except RealRunUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return runs.get_summary(run_id).model_dump(mode="json")

    @app.get("/api/runs/{run_id}")
    def run_status(run_id: str, request: Request) -> dict[str, object]:
        try:
            run = runs.get_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="run not found") from exc
        if run["llm_mode"] == "real":
            require_admin(request)
        return runs.get_summary(run_id).model_dump(mode="json")

    @app.get("/api/runs/{run_id}/events")
    def run_events(run_id: str) -> StreamingResponse:
        snapshot = current_snapshot()
        events = store(snapshot).list_events(run_id)

        def stream() -> Any:
            for event in events:
                yield f"event: {event['event_type']}\n"
                yield f"data: {json.dumps(public(event['payload'], snapshot), ensure_ascii=False)}\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/api/policies")
    def policies() -> dict[str, list[str]]:
        return {"profiles": ["strict_demo", "balanced_dev"]}

    @app.get("/api/credentials/status")
    def credential_status() -> dict[str, object]:
        snapshot = current_snapshot()
        return public(credentials.status(snapshot=snapshot), snapshot)

    @app.get("/api/memory")
    def memory_records(
        request: Request,
        scope: str = "project", query: str = "", tags: str = ""
    ) -> dict[str, object]:
        require_admin(request)
        snapshot = current_snapshot()
        records = MemoryService(store(snapshot)).search(
            tags=[tag for tag in tags.split(",") if tag],
            query=query,
            scope=scope,
            limit=100,
        )
        return public({"records": [record.model_dump(mode="json") for record in records]}, snapshot)

    @app.get("/api/approvals")
    def approval_queue(request: Request, state: str = "pending") -> dict[str, object]:
        require_admin(request)
        snapshot = current_snapshot()
        approvals_store = store(snapshot)
        try:
            parsed_state = ApprovalState(state) if state else None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid approval state") from exc
        approvals = ApprovalService(approvals_store).list(parsed_state)
        return public(
            {
                "approvals": [
                    approval.model_dump(mode="json", exclude={"feedback"})
                    for approval in approvals
                ]
            },
            snapshot,
        )

    @app.post("/api/approvals/{approval_id}/decision")
    def approval_decision(
        approval_id: str,
        decision: ApprovalDecisionRequest,
        request: Request,
    ) -> dict[str, object]:
        require_admin(request)
        require_same_origin(request)
        snapshot = current_snapshot()
        approvals = ApprovalService(store(snapshot))
        try:
            approval = approvals.get(approval_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="approval not found") from exc
        loop = app.state.pending_loops.get(approval.run_id)
        if loop is None:
            raise HTTPException(status_code=409, detail="approval run is not active")
        try:
            summary = loop.resolve_approval(
                approval_id,
                decision=decision.decision,
                reviewer=decision.reviewer,
                reason=decision.reason,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if summary.status != RunStatus.WAITING_APPROVAL.value:
            app.state.pending_loops.pop(approval.run_id, None)
        return public(
            {
                "approval_id": approval_id,
                "state": approvals.get(approval_id).state.value,
                "run": summary.model_dump(mode="json"),
            },
            snapshot,
        )

    _mount_frontend(app)

    return app


app = create_app()
