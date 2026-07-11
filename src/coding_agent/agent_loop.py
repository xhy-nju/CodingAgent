from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from coding_agent.action_parser import parse_action
from coding_agent.approvals import ApprovalService
from coding_agent.domain import ActionKind, FeedbackSignal, FeedbackType, RunStatus, ToolResult
from coding_agent.events import EventBus, EventType
from coding_agent.feedback import feedback_from_tool_result
from coding_agent.llm import LLMContext, LLMProvider
from coding_agent.memory import MemoryService
from coding_agent.store import SqliteStore
from coding_agent.tools.dispatcher import ToolDispatcher


class RunSummary(BaseModel):
    run_id: str
    status: str
    feedback: list[FeedbackSignal]
    pending_approval_id: str | None = None


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
        memory_scope: str = "project",
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
        self.memory_scope = memory_scope
        self.approvals = ApprovalService(store)

    def run(self, task: str) -> RunSummary:
        run_id = self.start_run(task)
        return self.continue_run(run_id)

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
            run_id,
            EventType.FEEDBACK_RECORDED,
            feedback.model_dump(mode="json"),
        )
        self.store.update_run_status(run_id, RunStatus.FAILED)
        self.events.append_event(
            run_id,
            EventType.RUN_FINISHED,
            {"status": "failed", "reason": reason},
        )
        return RunSummary(run_id=run_id, status="failed", feedback=[feedback])

    def _continue(
        self,
        run_id: str,
        task: str,
        start_step: int,
        feedback: list[FeedbackSignal],
    ) -> RunSummary:
        for step_index in range(start_step, self.max_steps):
            memories = tuple(
                self.memory.search(tags=[], query="", scope=self.memory_scope, limit=5)
            )
            raw = self.llm.next_action(
                LLMContext(
                    task=task,
                    step_index=step_index,
                    feedback=feedback,
                    memories=memories,
                )
            )
            self.events.append_event(run_id, EventType.LLM_OUTPUT, {"step": step_index, "raw": raw})
            parsed = parse_action(raw)
            if not parsed.ok:
                assert parsed.feedback is not None
                feedback = [parsed.feedback]
                self.events.append_event(
                    run_id, EventType.FEEDBACK_RECORDED, parsed.feedback.model_dump(mode="json")
                )
                continue

            action = parsed.action
            assert action is not None
            if action.kind is ActionKind.FINAL:
                self.store.update_run_status(run_id, RunStatus.SUCCEEDED)
                self.events.append_event(run_id, EventType.RUN_FINISHED, {"status": "succeeded"})
                return RunSummary(run_id=run_id, status="succeeded", feedback=feedback)
            if action.kind is ActionKind.REMEMBER:
                action = action.model_copy(
                    update={
                        "kind": ActionKind.TOOL,
                        "tool": "memory_write",
                        "args": action.args | {"source_run_id": run_id},
                    }
                )

            guardrail = self.dispatcher.evaluate(action)
            self.events.append_event(
                run_id,
                EventType.GUARDRAIL_CHECKED,
                {"action_id": action.id, **guardrail.model_dump(mode="json")},
            )
            result = self.dispatcher.dispatch(action, guardrail)
            if result.status == "needs_approval":
                approval = self.approvals.create(
                    run_id=run_id,
                    action=action,
                    rules=[str(rule) for rule in result.artifacts.get("rules", [])],
                    reason=result.stderr_summary,
                    step_index=step_index,
                    feedback=feedback,
                )
                self.store.update_run_status(run_id, RunStatus.WAITING_APPROVAL)
                self.events.append_event(
                    run_id,
                    EventType.APPROVAL_REQUESTED,
                    approval.model_dump(mode="json", exclude={"feedback"}),
                )
                return RunSummary(
                    run_id=run_id,
                    status=RunStatus.WAITING_APPROVAL.value,
                    feedback=feedback,
                    pending_approval_id=approval.id,
                )

            finished, feedback = self._record_tool_result(run_id, result)
            if finished is not None:
                return finished

        self.store.update_run_status(run_id, RunStatus.FAILED)
        self.events.append_event(
            run_id, EventType.RUN_FINISHED, {"status": "failed", "reason": "max_steps"}
        )
        return RunSummary(run_id=run_id, status="failed", feedback=feedback)

    def resolve_approval(
        self,
        approval_id: str,
        *,
        decision: str,
        reviewer: str,
        reason: str,
    ) -> RunSummary:
        request = self.approvals.get(approval_id)
        run = self.store.get_run(request.run_id)
        if decision == "approve":
            updated = self.approvals.approve_once(approval_id, reviewer, reason)
            self.events.append_event(
                request.run_id,
                EventType.APPROVAL_APPROVED,
                {"approval_id": approval_id, "reviewer": reviewer, "reason": reason},
            )
            self.store.update_run_status(request.run_id, RunStatus.RUNNING)
            result = self.dispatcher.execute_approved(updated.action)
            self.approvals.record_execution(approval_id, result)
            finished, feedback = self._record_tool_result(request.run_id, result)
            if finished is not None:
                return finished
        elif decision == "reject":
            self.approvals.reject(approval_id, reviewer, reason)
            self.events.append_event(
                request.run_id,
                EventType.APPROVAL_REJECTED,
                {"approval_id": approval_id, "reviewer": reviewer, "reason": reason},
            )
            feedback = [
                FeedbackSignal(
                    type=FeedbackType.APPROVAL_REJECTED,
                    severity="warning",
                    summary="Human reviewer rejected the requested action",
                    details={"approval_id": approval_id, "reason": reason},
                )
            ]
            self.events.append_event(
                request.run_id,
                EventType.FEEDBACK_RECORDED,
                feedback[0].model_dump(mode="json"),
            )
            self.store.update_run_status(request.run_id, RunStatus.RUNNING)
        else:
            raise ValueError(f"unsupported approval decision: {decision}")

        return self._continue(
            request.run_id,
            str(run["task"]),
            start_step=request.step_index + 1,
            feedback=feedback,
        )

    def _record_tool_result(
        self, run_id: str, result: ToolResult
    ) -> tuple[RunSummary | None, list[FeedbackSignal]]:
        self.events.append_event(run_id, EventType.TOOL_RESULT, result.model_dump(mode="json"))
        if result.artifacts.get("memory_id"):
            self.events.append_event(
                run_id,
                EventType.MEMORY_WRITTEN,
                {"memory_id": result.artifacts["memory_id"]},
            )
        feedback = feedback_from_tool_result(result)

        if result.status == "blocked":
            self.store.update_run_status(run_id, RunStatus.FAILED)
            self.events.append_event(run_id, EventType.RUN_FINISHED, {"status": "failed"})
            return RunSummary(run_id=run_id, status="failed", feedback=feedback), feedback

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
            self.events.append_event(
                run_id, EventType.FEEDBACK_RECORDED, item.model_dump(mode="json")
            )

        if any(item.type is FeedbackType.TEST_PASSED for item in feedback):
            self.store.update_run_status(run_id, RunStatus.SUCCEEDED)
            self.events.append_event(run_id, EventType.RUN_FINISHED, {"status": "succeeded"})
            return RunSummary(run_id=run_id, status="succeeded", feedback=feedback), feedback

        return None, feedback
