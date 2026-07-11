from pathlib import Path

import pytest

from coding_agent.action_parser import parse_action
from coding_agent.domain import ActionKind, FeedbackType
from coding_agent.policies import load_policy


def test_parse_valid_tool_action() -> None:
    result = parse_action(
        '{"kind":"tool","tool":"read_file","args":{"path":"calculator.py"},'
        '"reason":"inspect","expectation":"read file"}'
    )

    assert result.ok is True
    assert result.action is not None
    assert result.action.kind is ActionKind.TOOL
    assert result.action.tool == "read_file"


def test_parse_invalid_json_returns_schema_feedback() -> None:
    result = parse_action("not json")

    assert result.ok is False
    assert result.feedback is not None
    assert result.feedback.type is FeedbackType.SCHEMA_ERROR
    assert "valid JSON" in result.feedback.summary


def test_parse_unknown_kind_returns_schema_feedback() -> None:
    result = parse_action('{"kind":"unknown","reason":"x","expectation":"y","args":{}}')

    assert result.ok is False
    assert result.feedback is not None
    assert result.feedback.type is FeedbackType.SCHEMA_ERROR


def test_load_strict_policy() -> None:
    policy = load_policy("strict_demo", Path("config/policies"))

    assert policy.name == "strict_demo"
    assert "read_file" in policy.allowed_tools
    assert "rm" in policy.denied_command_fragments


@pytest.mark.parametrize(
    "raw",
    [
        '{"kind":"tool","args":{},"reason":"x","expectation":"y"}',
        '{"kind":"final","tool":"read_file","args":{},"reason":"x","expectation":"y"}',
        '{"kind":"final","args":{"unexpected":true},"reason":"x","expectation":"y"}',
        '{"kind":"remember","args":{},"reason":"x","expectation":"y"}',
        '{"kind":"remember","tool":"memory_write","args":{"content":"x"},"reason":"x","expectation":"y"}',
        '{"kind":"request_user","args":{},"reason":"x","expectation":"y"}',
    ],
)
def test_action_protocol_rejects_invalid_cross_field_shapes(raw: str) -> None:
    result = parse_action(raw)

    assert result.ok is False
    assert result.feedback is not None
    assert result.feedback.type is FeedbackType.SCHEMA_ERROR


@pytest.mark.parametrize(
    "raw",
    [
        '{"kind":"remember","args":{"content":"Prefer focused tests","tags":["pytest"]},"reason":"save","expectation":"memory"}',
        '{"kind":"request_user","args":{"question":"Which target?"},"reason":"clarify","expectation":"answer"}',
    ],
)
def test_action_protocol_accepts_explicit_non_tool_payloads(raw: str) -> None:
    assert parse_action(raw).ok is True
