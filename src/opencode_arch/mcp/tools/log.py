"""Record development decisions and progress to .architecture/devlog.jsonl."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


async def log_entry(
    repo_path: str,
    log_type: str,
    title: str,
    content: str = "",
    context: dict | None = None,
) -> dict[str, Any]:
    """Append a development log entry.

    Args:
        repo_path: Repository root path.
        log_type: "decision" | "progress" | "observation" | "issue" | "requirement"
        title: Short title (1 line).
        content: Optional longer description.
        context: Optional dict (files_changed, component_id, tool, etc.)
    """
    valid_types = {"decision", "progress", "observation", "issue", "requirement"}
    if log_type not in valid_types:
        return {"error": f"Invalid log_type. Must be one of: {valid_types}"}

    repo = Path(repo_path)
    arch_dir = repo / ".architecture"
    arch_dir.mkdir(parents=True, exist_ok=True)
    log_path = arch_dir / "devlog.jsonl"

    existing = 0
    if log_path.exists():
        existing = sum(1 for line in log_path.read_text().splitlines() if line.strip())

    entry = {
        "id": f"LOG-{existing + 1:04d}",
        "type": log_type,
        "title": title,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context": context or {},
    }

    with log_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")

    return {
        "logged": True,
        "entry_id": entry["id"],
        "total_entries": existing + 1,
        "log_type": log_type,
    }
