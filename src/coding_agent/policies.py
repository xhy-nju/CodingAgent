from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class PolicyProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    allowed_tools: list[str]
    allowed_command_prefixes: list[list[str]]
    denied_command_fragments: list[str]
    protected_path_fragments: list[str]
    max_file_bytes: int
    tool_timeout_seconds: int
    require_approval_tools: list[str]


def load_policy(name: str, config_dir: Path) -> PolicyProfile:
    path = config_dir / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Policy profile not found: {path}")
    return PolicyProfile.model_validate_json(path.read_text(encoding="utf-8"))
