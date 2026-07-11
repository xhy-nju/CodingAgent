from __future__ import annotations

import json
from pathlib import Path

from coding_agent.credentials import CredentialSnapshot
from coding_agent.llm import LLMContext, LLMProvider
from coding_agent.run_service import RunService


def _action(tool: str, args: dict[str, object]) -> str:
    return json.dumps(
        {
            "kind": "tool",
            "tool": tool,
            "args": args,
            "reason": "test action",
            "expectation": "test result",
        }
    )


class ScriptedProvider(LLMProvider):
    def __init__(self, actions: list[str]) -> None:
        self.actions = iter(actions)

    def next_action(self, context: LLMContext) -> str:
        return next(self.actions)


class FailingProvider(LLMProvider):
    def next_action(self, context: LLMContext) -> str:
        raise RuntimeError("transport failed with secret-real-token")


class ApprovalThenFinalProvider(LLMProvider):
    def next_action(self, context: LLMContext) -> str:
        if context.step_index == 0:
            return _action(
                "run_command",
                {"command": ["python", "-m", "pytest", "-q"]},
            )
        return json.dumps(
            {
                "kind": "final",
                "args": {},
                "reason": "approval complete",
                "expectation": "stop",
            }
        )


def _snapshot() -> CredentialSnapshot:
    return CredentialSnapshot(
        provider_token="secret-real-token",
        source="environment",
        base_url="https://example.test/v1",
        model="test-model",
        real_enabled=True,
    )


def test_real_run_uses_guarded_agent_loop(tmp_path: Path) -> None:
    provider = ScriptedProvider(
        [
            _action("run_tests", {"target": "."}),
            _action(
                "write_file",
                {
                    "path": "calculator.py",
                    "content": "def add(a, b):\n    return a + b\n",
                },
            ),
            _action("run_tests", {"target": "."}),
        ]
    )
    service = RunService(
        data_dir=tmp_path,
        credential_resolver=_snapshot,
        real_provider_factory=lambda snapshot: provider,
    )

    run_id = service.create_real_run("Repair the calculator", background=False)
    summary = service.get_summary(run_id)

    assert summary.status == "succeeded"
    run = service.store_for(_snapshot()).get_run(run_id)
    assert run["llm_mode"] == "real"
    assert Path(run["workspace"]).is_relative_to(tmp_path)


def test_real_run_failure_becomes_redacted_terminal_event(tmp_path: Path) -> None:
    service = RunService(
        data_dir=tmp_path,
        credential_resolver=_snapshot,
        real_provider_factory=lambda snapshot: FailingProvider(),
    )

    run_id = service.create_real_run("Fail safely", background=False)
    summary = service.get_summary(run_id)
    serialized = str(service.store_for(_snapshot()).list_events(run_id))

    assert summary.status == "failed"
    assert "secret-real-token" not in serialized
    assert "provider_token:redacted" in serialized


def test_real_run_requires_enabled_configured_credentials(tmp_path: Path) -> None:
    disabled = CredentialSnapshot(
        provider_token=None,
        source="missing",
        base_url="https://example.test/v1",
        model="test-model",
        real_enabled=False,
    )
    service = RunService(data_dir=tmp_path, credential_resolver=lambda: disabled)

    try:
        service.create_real_run("Repair calculator", background=False)
    except RuntimeError as exc:
        assert "not ready" in str(exc)
    else:
        raise AssertionError("real run should require enabled credentials")


def test_waiting_approval_resumes_after_service_reconstruction(tmp_path: Path) -> None:
    service = RunService(
        data_dir=tmp_path,
        credential_resolver=_snapshot,
        real_provider_factory=lambda snapshot: ApprovalThenFinalProvider(),
    )
    run_id = service.create_real_run("Run reviewed command", background=False)
    waiting = service.get_summary(run_id)
    assert waiting.status == "waiting_approval"
    assert waiting.pending_approval_id is not None

    reconstructed = RunService(
        data_dir=tmp_path,
        credential_resolver=_snapshot,
        real_provider_factory=lambda snapshot: ApprovalThenFinalProvider(),
    )
    resumed = reconstructed.resolve_approval(
        waiting.pending_approval_id,
        decision="approve",
        reviewer="admin",
        reason="command reviewed",
    )

    assert resumed.status == "succeeded"
    try:
        reconstructed.resolve_approval(
            waiting.pending_approval_id,
            decision="approve",
            reviewer="admin",
            reason="duplicate",
        )
    except ValueError as exc:
        assert "pending" in str(exc)
    else:
        raise AssertionError("approval must execute exactly once")
