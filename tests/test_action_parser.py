from pathlib import Path

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
