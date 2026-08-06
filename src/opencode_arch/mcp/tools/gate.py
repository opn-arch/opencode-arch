"""architect_gate MCP tool — check development gate readiness."""
from __future__ import annotations

from pathlib import Path
from typing import Any


async def check_gate(repo_path: str, model_yaml: str = "") -> dict[str, Any]:
    """Check development gate for an architecture model against code reality.

    Args:
        repo_path: Absolute path to the repository root.
        model_yaml: Optional YAML string. If empty, reads .architecture-model.yaml.

    Returns:
        Dict with lifecycle_phase, sub-scores, phase_requirements_met, and issues.
    """
    repo = Path(repo_path)
    if not repo.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}

    try:
        from architecture_model.authoring.gate import check_development_gate
        from architecture_model.core.parser import load_model
        from architecture_model.manifest.generator import generate_manifest

        # Load model
        if model_yaml:
            import yaml
            from architecture_model.core.parser import ArchitectureModel
            # Use load_model-compatible path: write temp then load, or parse directly
            from architecture_model.core.parser import _parse_raw
            raw = yaml.safe_load(model_yaml)
            model = _parse_raw(raw)
        else:
            model_path = repo / ".architecture-model.yaml"
            if not model_path.exists():
                return {"error": f"No model found at {model_path} and no model_yaml provided"}
            model = load_model(model_path)

        # Generate manifest
        manifest = generate_manifest(repo)

        # Determine phase
        phase = None
        if hasattr(model.meta, "lifecycle_phase"):
            phase = model.meta.lifecycle_phase

        # Run gate check
        result = check_development_gate(model, manifest, phase=phase)

        return {
            "lifecycle_phase": result.phase,
            "capability_realization": result.capability_realization,
            "constraint_allocation": result.constraint_allocation,
            "file_coverage": result.file_coverage,
            "overall": result.overall,
            "phase_requirements_met": result.phase_requirements_met,
            "issues": result.issues,
        }
    except Exception as e:
        return {"error": f"Gate check failed: {e}"}
