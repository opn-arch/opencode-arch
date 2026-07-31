"""Record user feedback for model improvement and training."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


async def record_feedback(
    repo_path: str,
    feedback_type: str,
    content: str,
    context: dict | None = None,
    rating: int | None = None,
    correction: dict | None = None,
) -> dict[str, Any]:
    """Record user feedback to .architecture/feedback.jsonl.
    
    Args:
        repo_path: Repository root path
        feedback_type: "correction" | "rating" | "tool_feedback" | "training"
        content: The feedback content (human-readable)
        context: Optional context dict (tool name, prompt, response, etc.)
        rating: Optional 1-5 quality rating
        correction: Optional structured correction {entity_id, field, old, new}
    
    Returns:
        {recorded, feedback_id, total_feedback}
    """
    repo = Path(repo_path)
    arch_dir = repo / ".architecture"
    arch_dir.mkdir(parents=True, exist_ok=True)
    feedback_path = arch_dir / "feedback.jsonl"
    
    # Count existing entries to generate ID
    existing_count = 0
    if feedback_path.exists():
        existing_count = sum(1 for line in feedback_path.read_text().splitlines() if line.strip())
    
    feedback_id = f"FB-{existing_count + 1}"
    
    # Build entry
    entry: dict[str, Any] = {
        "id": feedback_id,
        "type": feedback_type,
        "ts": datetime.now(timezone.utc).isoformat(),
        "content": content,
    }
    if context:
        entry["context"] = context
    if rating is not None:
        entry["rating"] = rating
    if correction:
        entry["correction"] = correction
    
    # Append to JSONL
    with feedback_path.open("a") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    
    return {
        "recorded": True,
        "feedback_id": feedback_id,
        "total_feedback": existing_count + 1,
    }
