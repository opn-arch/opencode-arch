"""architect_check MCP tool — verify model representativeness against code reality."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import yaml


async def check_representativeness(repo_path: str, model_yaml: str) -> dict[str, Any]:
    """Check how well an architecture model represents the actual codebase.

    Computes three mechanical sub-scores:
    1. File Coverage — % of source files mapped to components
    2. Relationship Accuracy — % of model relationships backed by real imports
    3. Boundary Coherence — avg internal cohesion of component groupings

    Args:
        repo_path: Absolute path to the repository root.
        model_yaml: The architecture model YAML to evaluate.

    Returns:
        Dict with scores, details, and suggested improvements.
    """
    path = Path(repo_path)
    if not path.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}

    try:
        from architecture_model.manifest.generator import generate_manifest
        from architecture_model.core.parser import load_model
        from architecture_model.core.representativeness import compute_representativeness as _compute

        # Generate ground truth manifest
        manifest = generate_manifest(path)

        # Parse the model via temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(model_yaml)
            tmp_path = f.name

        try:
            model = load_model(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        # Compute representativeness
        result = _compute(model, manifest.modules, manifest.interfaces)

        output = {
            "file_coverage": round(result.file_coverage, 1),
            "relationship_accuracy": round(result.relationship_accuracy, 1),
            "boundary_coherence": round(result.boundary_coherence, 1),
            "overall": round(result.overall, 1),
            "uncovered_files": result.uncovered_files,
            "unverified_relationships": result.unverified_relationships,
            "low_coherence_components": result.low_coherence_components,
        }

        try:
            from opencode_arch.telemetry.collector import drain_and_store
            drain_and_store(tool="architect_check", repo=path.name)
        except Exception:
            pass

        return output

    except Exception as e:
        return {"error": f"Check failed: {e}"}
