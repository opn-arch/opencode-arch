"""Record development decisions and progress to .architecture/devlog.jsonl."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


async def log_entry(
    repo_path: str,
    log_type: str = "",
    title: str = "",
    content: str = "",
    context: dict | None = None,
    batch: bool = False,
    entries: str = "",
) -> dict[str, Any]:
    """Append a development log entry (single or batch).

    Args:
        repo_path: Repository root path.
        log_type: "decision" | "progress" | "observation" | "issue" | "requirement"
        title: Short title (1 line).
        content: Optional longer description.
        context: Optional dict (files_changed, component_id, tool, etc.)
        batch: If True, parse `entries` as JSON array of objects.
        entries: JSON string of [{log_type, title, content?, context?}, ...] when batch=True.
    """
    valid_types = {"decision", "progress", "observation", "issue", "requirement"}

    repo = Path(repo_path)
    arch_dir = repo / ".architecture"
    arch_dir.mkdir(parents=True, exist_ok=True)
    log_path = arch_dir / "devlog.jsonl"

    existing = 0
    if log_path.exists():
        existing = sum(1 for line in log_path.read_text().splitlines() if line.strip())

    if batch:
        try:
            items = json.loads(entries)
        except (json.JSONDecodeError, TypeError) as e:
            return {"error": f"Failed to parse entries JSON: {e}"}
        if not isinstance(items, list):
            return {"error": "entries must be a JSON array"}

        logged_ids = []
        with log_path.open("a") as f:
            for item in items:
                lt = item.get("log_type", item.get("event", ""))
                if lt not in valid_types:
                    return {
                        "error": f"Invalid log_type '{lt}' in batch entry. Must be one of: {valid_types}"
                    }
                existing += 1
                entry = {
                    "id": f"LOG-{existing:04d}",
                    "type": lt,
                    "title": item.get("title", item.get("detail", "")),
                    "content": item.get("content", ""),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "context": item.get("context", item.get("tags", {})),
                }
                f.write(json.dumps(entry) + "\n")
                logged_ids.append(entry["id"])

        return {
            "logged": True,
            "batch": True,
            "entry_ids": logged_ids,
            "total_entries": existing,
            "count": len(logged_ids),
        }

    # Single entry mode
    if log_type not in valid_types:
        return {"error": f"Invalid log_type. Must be one of: {valid_types}"}

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
