from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import typer

from coding_agent.agent_loop import AgentLoop
from coding_agent.credentials import CredentialService
from coding_agent.events import EventBus
from coding_agent.guardrails import GuardrailEngine
from coding_agent.llm import MockLLMProvider
from coding_agent.llm_probe import probe_real_llm
from coding_agent.memory import MemoryService
from coding_agent.policies import load_policy
from coding_agent.store import SqliteStore
from coding_agent.tools.dispatcher import build_default_dispatcher

app = typer.Typer(help="CodingAgent harness CLI")
credentials_app = typer.Typer(help="Credential commands")
app.add_typer(credentials_app, name="credentials")
llm_app = typer.Typer(help="LLM provider commands")
app.add_typer(llm_app, name="llm")


@app.callback()
def main() -> None:
    pass


def _copy_sample_workspace() -> Path:
    tempdir = Path(tempfile.mkdtemp(prefix="coding-agent-demo-"))
    shutil.copytree(Path("demos/sample_workspace"), tempdir / "workspace")
    return tempdir / "workspace"


def _build_loop(workspace: Path, db_path: Path, script_name: str) -> AgentLoop:
    store = SqliteStore(db_path)
    policy = load_policy("strict_demo", Path("config/policies"))
    memory = MemoryService(store)
    dispatcher = build_default_dispatcher(
        GuardrailEngine(policy, workspace),
        workspace,
        policy,
        memory=memory,
    )
    return AgentLoop(
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


@app.command()
def demo(name: str = typer.Argument(..., help="dangerous-action or bugfix")) -> None:
    if name == "dangerous-action":
        script_name = "dangerous_action"
        workspace = Path(tempfile.mkdtemp(prefix="coding-agent-empty-"))
    elif name == "bugfix":
        script_name = "bugfix_with_feedback"
        workspace = _copy_sample_workspace()
    else:
        raise typer.BadParameter("expected 'dangerous-action' or 'bugfix'")

    loop = _build_loop(workspace, workspace.parent / "agent.db", script_name)
    summary = loop.run(f"demo {name}")
    typer.echo(json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2))
    raise typer.Exit(code=0 if summary.status == "succeeded" else 1)


def _credential_service() -> CredentialService:
    return CredentialService()


def _credential_status_json() -> str:
    return json.dumps(_credential_service().status(), ensure_ascii=False, indent=2)


@credentials_app.command("status", hidden=True)
def credentials_status() -> None:
    typer.echo(_credential_status_json())


@app.command("credentials-status")
def credentials_status_alias() -> None:
    typer.echo(_credential_status_json())


def _set_keyring_token() -> None:
    token = typer.prompt("API key", hide_input=True, confirmation_prompt=True)
    _credential_service().set_keyring_token(token)
    typer.echo("Keyring credential saved.")


@credentials_app.command("set", hidden=True)
def credentials_set() -> None:
    _set_keyring_token()


@credentials_app.command("update", hidden=True)
def credentials_update() -> None:
    _set_keyring_token()


@credentials_app.command("clear", hidden=True)
def credentials_clear() -> None:
    removed = _credential_service().clear_keyring_token()
    if removed:
        typer.echo("Keyring credential removed. Environment and Docker Secret sources are unaffected.")
    else:
        typer.echo("No Keyring credential was present. Environment and Docker Secret sources are unaffected.")


@llm_app.command("probe")
def llm_probe() -> None:
    result = probe_real_llm(_credential_service().resolve())
    typer.echo(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    if not result.ok:
        raise typer.Exit(code=1)
