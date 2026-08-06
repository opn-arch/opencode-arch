"""architect_correct MCP tool — store structured architecture corrections."""
from __future__ import annotations
from pathlib import Path
from typing import Any


async def store_correction(
    repo_path: str,
    correction_type: str,
    target: str,
    reason: str,
    suggestion: dict | None = None,
) -> dict[str, Any]:
    """Store a structured correction for the architecture model.
    
    Corrections are consumed on next pipeline run to improve the model.
    
    Args:
        repo_path: Absolute path to the repository.
        correction_type: One of: split_component, merge_components, add_component,
            remove_component, add_relationship, remove_relationship, rename, reclassify.
        target: Entity ID being corrected (e.g., "COMP-3").
        reason: Why this correction is needed.
        suggestion: Optional structured suggestion (format depends on type).
    """
    path = Path(repo_path)
    if not path.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}
    
    valid_types = {
        "split_component", "merge_components", "add_component", "remove_component",
        "add_relationship", "remove_relationship", "rename", "reclassify",
    }
    if correction_type not in valid_types:
        return {"error": f"Invalid correction_type: {correction_type}. Must be one of: {sorted(valid_types)}"}
    
    correction = {
        "type": correction_type,
        "target": target,
        "reason": reason,
    }
    if suggestion:
        correction["suggestion"] = suggestion
    
    try:
        from architecture_model.core.corrections import store_correction as _store
        stored = _store(path, correction)
        return {"stored": True, "correction": stored}
    except ImportError:
        # Fallback: write directly
        import yaml
        from datetime import datetime, timezone
        
        arch_dir = path / ".architecture"
        arch_dir.mkdir(exist_ok=True)
        corrections_file = arch_dir / "corrections.yaml"
        
        if corrections_file.exists():
            data = yaml.safe_load(corrections_file.read_text()) or {}
        else:
            data = {}
        
        corrections_list = data.get("corrections", [])
        next_id = len(corrections_list) + 1
        correction["id"] = f"COR-{next_id}"
        correction["applied"] = False
        correction["created_at"] = datetime.now(timezone.utc).isoformat()
        corrections_list.append(correction)
        data["corrections"] = corrections_list
        corrections_file.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
        
        return {"stored": True, "correction": correction}
    except Exception as e:
        return {"error": f"Failed to store correction: {e}"}
