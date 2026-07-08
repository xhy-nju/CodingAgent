from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from coding_agent.agent_loop import AgentLoop
from coding_agent.credentials import CredentialService
from coding_agent.events import EventBus
from coding_agent.guardrails import GuardrailEngine
from coding_agent.llm import MockLLMProvider
from coding_agent.memory import MemoryService
from coding_agent.policies import load_policy
from coding_agent.store import SqliteStore
from coding_agent.tools.dispatcher import build_default_dispatcher


class DemoRequest(BaseModel):
    name: str


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


def _run_demo(name: str, data_dir: Path) -> dict[str, Any]:
    workspace = _workspace_for_demo(name, data_dir)
    store = SqliteStore(data_dir / "agent.db")
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
    return loop.run(f"demo {name}").model_dump(mode="json")


def _frontend_dist_dir() -> Path:
    return Path(os.environ.get("CODING_AGENT_FRONTEND_DIST", "frontend/dist"))


def _mount_frontend(app: FastAPI) -> None:
    frontend_dist = _frontend_dist_dir()
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


def create_app(data_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="CodingAgent Harness")
    runtime_dir = data_dir or Path(os.environ.get("CODING_AGENT_DATA_DIR", ".coding-agent-data"))

    def ensure_runtime_dir() -> Path:
        runtime_dir.mkdir(parents=True, exist_ok=True)
        return runtime_dir

    @app.post("/api/runs/demo")
    def create_demo_run(request: DemoRequest) -> dict[str, Any]:
        return _run_demo(request.name, ensure_runtime_dir())

    @app.get("/api/runs/{run_id}/events")
    def run_events(run_id: str) -> StreamingResponse:
        store = SqliteStore(ensure_runtime_dir() / "agent.db")
        events = store.list_events(run_id)

        def stream() -> Any:
            for event in events:
                yield f"event: {event['event_type']}\n"
                yield f"data: {json.dumps(event['payload'], ensure_ascii=False)}\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/api/policies")
    def policies() -> dict[str, list[str]]:
        return {"profiles": ["strict_demo", "balanced_dev"]}

    @app.get("/api/credentials/status")
    def credential_status() -> dict[str, object]:
        return CredentialService.from_env().status()

    @app.post("/api/approvals/{approval_id}/decision")
    def approval_decision(approval_id: str) -> dict[str, str]:
        return {"approval_id": approval_id, "state": "recorded"}

    _mount_frontend(app)

    return app


app = create_app()
