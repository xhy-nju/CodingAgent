from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from coding_agent.domain import ToolResult
from coding_agent.policies import PolicyProfile


class ToolContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    workspace: Path
    policy: PolicyProfile
    memory: Any | None = None


class ToolSpec(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    handler: Callable[[dict[str, Any], ToolContext], ToolResult]
