from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from coding_agent.domain import Action, FeedbackSignal, FeedbackType


class ParseResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ok: bool
    action: Action | None = None
    feedback: FeedbackSignal | None = None
    raw: str


def _schema_error(summary: str, raw: str, details: dict[str, Any] | None = None) -> ParseResult:
    return ParseResult(
        ok=False,
        raw=raw,
        feedback=FeedbackSignal(
            type=FeedbackType.SCHEMA_ERROR,
            severity="error",
            summary=summary,
            details=details or {},
        ),
    )


def parse_action(raw: str) -> ParseResult:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return _schema_error("LLM output must be valid JSON", raw, {"error": str(exc)})

    if not isinstance(payload, dict):
        return _schema_error("LLM output JSON must be an object", raw)

    try:
        action = Action.model_validate(payload)
    except ValidationError as exc:
        return _schema_error("LLM action failed schema validation", raw, {"errors": exc.errors()})

    if action.kind == "tool" and not action.tool:
        return _schema_error("Tool action must include tool name", raw)

    return ParseResult(ok=True, raw=raw, action=action)
