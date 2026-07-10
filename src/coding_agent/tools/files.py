from __future__ import annotations

import os
import tempfile
from pathlib import Path

from coding_agent.domain import ToolResult
from coding_agent.tools.base import ToolContext


IGNORED_PARTS = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}


def _resolve_inside(workspace: Path, relative_path: str) -> Path:
    candidate = (workspace / relative_path).resolve()
    root = workspace.resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("path outside workspace")
    return candidate


def list_files(args: dict[str, object], context: ToolContext) -> ToolResult:
    files: list[str] = []
    for path in sorted(context.workspace.rglob("*")):
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        if path.is_file():
            files.append(path.relative_to(context.workspace).as_posix())
    return ToolResult(status="ok", artifacts={"files": files})


def read_file(args: dict[str, object], context: ToolContext) -> ToolResult:
    relative = str(args["path"])
    path = _resolve_inside(context.workspace, relative)
    content = path.read_text(encoding="utf-8")
    if len(content.encode("utf-8")) > context.policy.max_file_bytes:
        return ToolResult(status="failed", stderr_summary=f"file too large: {relative}")
    return ToolResult(status="ok", artifacts={"path": relative, "content": content})


def write_file(args: dict[str, object], context: ToolContext) -> ToolResult:
    relative = str(args["path"])
    content = str(args["content"])
    encoded = content.encode("utf-8")
    if len(encoded) > context.policy.max_file_bytes:
        return ToolResult(
            status="failed",
            stderr_summary=(
                f"content exceeds maximum file size of {context.policy.max_file_bytes} bytes"
            ),
        )
    path = _resolve_inside(context.workspace, relative)
    existed = path.exists()
    before = path.read_text(encoding="utf-8") if existed else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    if existed:
        diff_summary = (
            f"updated {relative}: {len(before.splitlines())} lines -> "
            f"{len(content.splitlines())} lines"
        )
    else:
        diff_summary = f"created {relative}"
    return ToolResult(status="ok", artifacts={"path": relative, "diff_summary": diff_summary})
