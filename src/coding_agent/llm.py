from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from coding_agent.domain import FeedbackSignal, MemoryRecord
from coding_agent.credentials import CredentialService, CredentialSnapshot


@dataclass(frozen=True)
class LLMContext:
    task: str
    step_index: int
    feedback: list[FeedbackSignal]
    memories: tuple[MemoryRecord, ...] = ()
    max_completion_tokens: int = 512


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


class RealLLMProvider(LLMProvider):
    def __init__(
        self,
        provider_token: str | None,
        base_url: str,
        model: str,
        enabled: bool,
    ) -> None:
        self.provider_token = provider_token
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.enabled = enabled

    @classmethod
    def from_credentials(cls, snapshot: CredentialSnapshot) -> "RealLLMProvider":
        return cls(
            provider_token=snapshot.provider_token,
            base_url=snapshot.base_url,
            model=snapshot.model,
            enabled=snapshot.real_enabled,
        )

    @classmethod
    def from_env(cls) -> "RealLLMProvider":
        return cls.from_credentials(CredentialService().resolve())

    def next_action(self, context: LLMContext) -> str:
        if not self.enabled:
            raise RuntimeError("Real LLM is disabled; set ENABLE_REAL_LLM=true to enable it")
        if not self.provider_token:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        memory_text = "\n".join(f"- {record.content}" for record in context.memories)
        user_content = f"Task: {context.task}\nStep: {context.step_index}"
        if memory_text:
            user_content += f"\nRelevant memory:\n{memory_text}"
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.provider_token}"},
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Return exactly one strict JSON CodingAgent action.",
                    },
                    {
                        "role": "user",
                        "content": user_content,
                    },
                ],
                "temperature": 0,
                "max_tokens": context.max_completion_tokens,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("provider assistant content must be a non-empty string")
        return content
