from __future__ import annotations

from pathlib import Path

from coding_agent.domain import Action, GuardrailDecision, GuardrailDecisionType
from coding_agent.policies import PolicyProfile


class GuardrailEngine:
    def __init__(self, policy: PolicyProfile, workspace: Path) -> None:
        self.policy = policy
        self.workspace = workspace.resolve()

    def evaluate(self, action: Action) -> GuardrailDecision:
        rules: list[str] = []

        if action.tool not in self.policy.allowed_tools:
            return GuardrailDecision(
                decision=GuardrailDecisionType.DENY,
                rules=["tool.not_allowed"],
                message=f"Tool is not allowed by policy: {action.tool}",
            )

        path_value = action.args.get("path") or action.args.get("target")
        if isinstance(path_value, str) and self._path_is_unsafe(path_value):
            rules.append("path.outside_workspace")

        command = action.args.get("command")
        if isinstance(command, list):
            command_text = " ".join(str(part) for part in command)
            if any(fragment in command_text for fragment in self.policy.denied_command_fragments):
                rules.append("command.denied_fragment")
            if action.tool == "run_command" and not self._command_prefix_allowed(command):
                rules.append("command.prefix_not_allowed")

        for value in action.args.values():
            if isinstance(value, str) and any(
                fragment in value for fragment in self.policy.protected_path_fragments
            ):
                rules.append("path.protected_fragment")

        if rules:
            return GuardrailDecision(
                decision=GuardrailDecisionType.DENY,
                rules=sorted(set(rules)),
                message="Action violates guardrail policy",
            )

        if action.tool in self.policy.require_approval_tools:
            return GuardrailDecision(
                decision=GuardrailDecisionType.NEEDS_APPROVAL,
                rules=["tool.requires_approval"],
                message="Tool requires human approval in this policy",
            )

        return GuardrailDecision(
            decision=GuardrailDecisionType.ALLOW,
            rules=[],
            message="Action allowed",
        )

    def _path_is_unsafe(self, path_value: str) -> bool:
        candidate = (self.workspace / path_value).resolve()
        return not candidate.is_relative_to(self.workspace)

    def _command_prefix_allowed(self, command: list[object]) -> bool:
        normalized = [str(part) for part in command]
        return any(
            normalized[: len(prefix)] == prefix for prefix in self.policy.allowed_command_prefixes
        )
