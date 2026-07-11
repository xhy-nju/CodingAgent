from __future__ import annotations

import os
import shutil
import uuid
from concurrent.futures import Executor, ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from pydantic import ValidationError

from coding_agent.agent_loop import AgentLoop, RunSummary
from coding_agent.approvals import ApprovalService
from coding_agent.credentials import CredentialService, CredentialSnapshot
from coding_agent.domain import ApprovalState, FeedbackSignal
from coding_agent.events import EventBus
from coding_agent.guardrails import GuardrailEngine
from coding_agent.llm import LLMProvider, MockLLMProvider, RealLLMProvider
from coding_agent.memory import MemoryService
from coding_agent.policies import load_policy
from coding_agent.redaction import redact_value
from coding_agent.store import SqliteStore
from coding_agent.tools.dispatcher import build_default_dispatcher


class RealRunUnavailable(RuntimeError):
    pass


class RunService:
    def __init__(
        self,
        data_dir: Path,
        *,
        credential_resolver: Callable[[], CredentialSnapshot] | None = None,
        real_provider_factory: Callable[[CredentialSnapshot], LLMProvider] | None = None,
        executor: Executor | None = None,
    ) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.credential_resolver = credential_resolver or CredentialService().resolve
        self.real_provider_factory = real_provider_factory or RealLLMProvider.from_credentials
        self.executor = executor or ThreadPoolExecutor(
            max_workers=int(os.environ.get("REAL_RUN_WORKERS", "2")),
            thread_name_prefix="coding-agent-real",
        )
        SqliteStore(self.data_dir / "agent.db").fail_interrupted_runs()

    def store_for(self, snapshot: CredentialSnapshot) -> SqliteStore:
        return SqliteStore(
            self.data_dir / "agent.db", credential_snapshot=snapshot
        )

    def create_real_run(self, task: str, *, background: bool = True) -> str:
        normalized_task = task.strip()
        if not 1 <= len(normalized_task) <= 4000:
            raise ValueError("task must contain between 1 and 4000 characters")
        snapshot = self.credential_resolver()
        if not snapshot.real_enabled or not snapshot.configured:
            raise RealRunUnavailable("real LLM is not ready")

        workspace = self._copy_sample_workspace()
        loop = self._build_loop(
            workspace,
            self.real_provider_factory(snapshot),
            snapshot,
            llm_mode="real",
        )
        run_id = loop.start_run(normalized_task)
        if background:
            self.executor.submit(self._execute, loop, run_id, snapshot)
        else:
            self._execute(loop, run_id, snapshot)
        return run_id

    def get_run(self, run_id: str) -> dict[str, object]:
        return self.store_for(self.credential_resolver()).get_run(run_id)

    def get_summary(self, run_id: str) -> RunSummary:
        snapshot = self.credential_resolver()
        store = self.store_for(snapshot)
        run = store.get_run(run_id)
        feedback: list[FeedbackSignal] = []
        for event in store.list_events(run_id):
            if event["event_type"] != "feedback.recorded":
                continue
            try:
                feedback.append(FeedbackSignal.model_validate(event["payload"]))
            except ValidationError:
                continue
        pending = next(
            (
                approval.id
                for approval in ApprovalService(store).list(ApprovalState.PENDING)
                if approval.run_id == run_id
            ),
            None,
        )
        return RunSummary(
            run_id=run_id,
            status=str(run["status"]),
            feedback=feedback,
            pending_approval_id=pending,
        )

    def resolve_approval(
        self,
        approval_id: str,
        *,
        decision: str,
        reviewer: str,
        reason: str,
    ) -> RunSummary:
        snapshot = self.credential_resolver()
        store = self.store_for(snapshot)
        approval = ApprovalService(store).get(approval_id)
        run = store.get_run(approval.run_id)
        llm_mode = str(run["llm_mode"])
        if llm_mode == "real":
            if not snapshot.real_enabled or not snapshot.configured:
                raise RealRunUnavailable("real LLM is not ready")
            provider = self.real_provider_factory(snapshot)
        else:
            script_name = (
                "dangerous_action"
                if "dangerous-action" in str(run["task"])
                else "bugfix_with_feedback"
            )
            provider = MockLLMProvider(script_name)
        loop = self._build_loop(
            Path(str(run["workspace"])),
            provider,
            snapshot,
            llm_mode=llm_mode,
        )
        return loop.resolve_approval(
            approval_id,
            decision=decision,
            reviewer=reviewer,
            reason=reason,
        )

    def _copy_sample_workspace(self) -> Path:
        run_root = self.data_dir / "run-workspaces" / f"real-{uuid.uuid4().hex[:12]}"
        workspace = run_root / "workspace"
        run_root.mkdir(parents=True, exist_ok=False)
        shutil.copytree(Path("demos/sample_workspace"), workspace)
        return workspace

    def _build_loop(
        self,
        workspace: Path,
        provider: LLMProvider,
        snapshot: CredentialSnapshot,
        *,
        llm_mode: str,
    ) -> AgentLoop:
        store = self.store_for(snapshot)
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
            llm=provider,
            workspace=workspace,
            policy_profile="strict_demo",
            llm_mode=llm_mode,
            max_steps=8,
        )

    @staticmethod
    def _execute(
        loop: AgentLoop, run_id: str, snapshot: CredentialSnapshot
    ) -> None:
        try:
            loop.continue_run(run_id)
        except Exception as exc:
            reason = str(redact_value(str(exc), snapshot.provider_token)[0])[:500]
            loop.fail_run(run_id, reason or "real provider execution failed")
