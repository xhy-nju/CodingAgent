from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from coding_agent.action_parser import parse_action
from coding_agent.domain import ActionKind, FeedbackSignal, FeedbackType, RunStatus
from coding_agent.events import EventBus
from coding_agent.feedback import feedback_from_tool_result
from coding_agent.llm import LLMContext, LLMProvider
from coding_agent.memory import MemoryService
from coding_agent.store import SqliteStore
from coding_agent.tools.dispatcher import ToolDispatcher


class RunSummary(BaseModel):
    run_id: str
    status: str
    feedback: list[FeedbackSignal]


class AgentLoop:
    def __init__(
        self,
        store: SqliteStore,
        events: EventBus,
        memory: MemoryService,
        dispatcher: ToolDispatcher,
        llm: LLMProvider,
        workspace: Path,
        policy_profile: str,
        llm_mode: str,
        max_steps: int,
    ) -> None:
        self.store = store
        self.events = events
        self.memory = memory
        self.dispatcher = dispatcher
        self.llm = llm
        self.workspace = workspace
        self.policy_profile = policy_profile
        self.llm_mode = llm_mode
        self.max_steps = max_steps

    def run(self, task: str) -> RunSummary:
        run_id = self.store.create_run(task, str(self.workspace), self.policy_profile, self.llm_mode)
        self.store.update_run_status(run_id, RunStatus.RUNNING)
        self.events.append_event(run_id, "run.started", {"task": task})
        feedback: list[FeedbackSignal] = []

        for step_index in range(self.max_steps):
            raw = self.llm.next_action(LLMContext(task=task, step_index=step_index, feedback=feedback))
            self.events.append_event(run_id, "llm.raw", {"step": step_index, "raw": raw})
            parsed = parse_action(raw)
            if not parsed.ok:
                assert parsed.feedback is not None
                feedback = [parsed.feedback]
                self.events.append_event(run_id, "feedback", parsed.feedback.model_dump(mode="json"))
                continue

            action = parsed.action
            assert action is not None
            if action.kind is ActionKind.FINAL:
                self.store.update_run_status(run_id, RunStatus.SUCCEEDED)
                self.events.append_event(run_id, "run.finished", {"status": "succeeded"})
                return RunSummary(run_id=run_id, status="succeeded", feedback=feedback)

            result = self.dispatcher.dispatch(action)
            self.events.append_event(run_id, "tool.result", result.model_dump(mode="json"))
            feedback = feedback_from_tool_result(result)

            if result.status == "blocked":
                self.store.update_run_status(run_id, RunStatus.FAILED)
                self.events.append_event(run_id, "run.finished", {"status": "failed"})
                return RunSummary(run_id=run_id, status="failed", feedback=feedback)

            if result.artifacts.get("diff_summary"):
                feedback = [
                    FeedbackSignal(
                        type=FeedbackType.FILE_DIFF,
                        severity="info",
                        summary=result.artifacts["diff_summary"],
                        details=result.artifacts,
                    )
                ]

            for item in feedback:
                self.events.append_event(run_id, "feedback", item.model_dump(mode="json"))

            if any(item.type is FeedbackType.TEST_PASSED for item in feedback):
                self.store.update_run_status(run_id, RunStatus.SUCCEEDED)
                self.events.append_event(run_id, "run.finished", {"status": "succeeded"})
                return RunSummary(run_id=run_id, status="succeeded", feedback=feedback)

        self.store.update_run_status(run_id, RunStatus.FAILED)
        self.events.append_event(run_id, "run.finished", {"status": "failed", "reason": "max_steps"})
        return RunSummary(run_id=run_id, status="failed", feedback=feedback)
