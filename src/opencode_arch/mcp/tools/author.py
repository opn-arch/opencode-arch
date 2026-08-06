"""architect_author MCP tool — forward-author architecture from requirements."""
from __future__ import annotations

from pathlib import Path
from typing import Any


async def author_architecture(repo_path: str, requirements_text: str) -> dict[str, Any]:
    """Parse requirements text and produce a concept-phase architecture model.

    Args:
        repo_path: Absolute path to the repository root.
        requirements_text: Free-form or structured requirements document text.

    Returns:
        Dict with model_path, entity counts, and lifecycle_phase.
    """
    path = Path(repo_path)
    if not path.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}

    try:
        from architecture_model.authoring.parser import parse_requirements_doc
        from architecture_model.core.parser import save_model

        model = parse_requirements_doc(requirements_text)

        # Set lifecycle_phase if the field exists on meta
        if hasattr(model.meta, "lifecycle_phase"):
            model.meta.lifecycle_phase = "concept"

        output_path = path / ".architecture-model.yaml"
        save_model(model, output_path)

        return {
            "model_path": str(output_path),
            "actors": len(model.entities.actors) if model.entities.actors else 0,
            "capabilities": len(model.entities.capabilities) if model.entities.capabilities else 0,
            "constraints": len(model.entities.constraints) if model.entities.constraints else 0,
            "relationships": len(model.relationships),
            "lifecycle_phase": "concept",
        }
    except Exception as e:
        return {"error": f"Author failed: {e}"}
