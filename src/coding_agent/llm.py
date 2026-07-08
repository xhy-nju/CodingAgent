from __future__ import annotations

import json
from dataclasses import dataclass

from coding_agent.domain import FeedbackSignal


@dataclass(frozen=True)
class LLMContext:
    task: str
    step_index: int
    feedback: list[FeedbackSignal]


class LLMProvider:
    def next_action(self, context: LLMContext) -> str:
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    def __init__(self, script_name: str) -> None:
        self.script_name = script_name

    def next_action(self, context: LLMContext) -> str:
        if self.script_name == "dangerous_action":
            return json.dumps(
                {
                    "kind": "tool",
                    "tool": "read_file",
                    "args": {"path": "../outside.txt"},
                    "reason": "attempt unsafe read",
                    "expectation": "guardrail blocks it",
                }
            )
        if self.script_name == "bugfix_with_feedback":
            return self._bugfix_action(context)
        raise ValueError(f"unknown mock script: {self.script_name}")

    def _bugfix_action(self, context: LLMContext) -> str:
        feedback_types = {item.type.value for item in context.feedback}
        if context.step_index == 0:
            payload = {
                "kind": "tool",
                "tool": "run_tests",
                "args": {"target": "."},
                "reason": "observe failing tests",
                "expectation": "pytest failure summary",
            }
        elif "test_failed" in feedback_types and context.step_index == 1:
            payload = {
                "kind": "tool",
                "tool": "write_file",
                "args": {"path": "calculator.py", "content": "def add(a, b):\n    return a * b\n"},
                "reason": "first attempted fix",
                "expectation": "tests may still fail",
            }
        elif "file_diff" in feedback_types or context.step_index == 2:
            payload = {
                "kind": "tool",
                "tool": "run_tests",
                "args": {"target": "."},
                "reason": "check first fix",
                "expectation": "feedback tells whether fix worked",
            }
        elif "test_failed" in feedback_types:
            payload = {
                "kind": "tool",
                "tool": "write_file",
                "args": {"path": "calculator.py", "content": "def add(a, b):\n    return a + b\n"},
                "reason": "apply correct addition fix",
                "expectation": "tests pass after rerun",
            }
        else:
            payload = {
                "kind": "final",
                "args": {},
                "reason": "task complete",
                "expectation": "agent stops",
            }
        return json.dumps(payload)
