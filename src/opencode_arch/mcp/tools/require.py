"""Capture functional requirements against architecture components."""
from __future__ import annotations

import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


async def capture_requirement(
    repo_path: str,
    requirement: str,
    component_id: str | None = None,
    priority: str = "must",
    context: str = "",
) -> dict[str, Any]:
    """Store a functional requirement linked to a component.
    
    Args:
        repo_path: Repository root path
        requirement: The requirement text
        component_id: Component ID (e.g., "COMP-3"). If None, stored as unlinked.
        priority: must | should | could (MoSCoW)
        context: Additional context from conversation
    
    Returns:
        {stored, requirement_id, component, total_requirements}
    """
    repo = Path(repo_path)
    arch_dir = repo / ".architecture"
    arch_dir.mkdir(parents=True, exist_ok=True)
    req_path = arch_dir / "requirements.yaml"
    
    # Load existing
    if req_path.exists():
        data = yaml.safe_load(req_path.read_text()) or {}
    else:
        data = {}
    
    reqs = data.get("requirements", [])
    
    # Generate next ID
    existing_ids = [r.get("id", "") for r in reqs]
    max_num = 0
    for rid in existing_ids:
        if rid.startswith("REQ-"):
            try:
                max_num = max(max_num, int(rid[4:]))
            except ValueError:
                pass
    next_id = f"REQ-{max_num + 1}"
    
    # Build requirement entry
    entry = {
        "id": next_id,
        "text": requirement,
        "priority": priority,
        "status": "proposed",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if component_id:
        entry["component"] = component_id
    if context:
        entry["context"] = context
    
    reqs.append(entry)
    data["requirements"] = reqs
    
    # Write back
    req_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    
    return {
        "stored": True,
        "requirement_id": next_id,
        "component": component_id or "unlinked",
        "total_requirements": len(reqs),
    }
