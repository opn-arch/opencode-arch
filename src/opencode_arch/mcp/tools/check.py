"""architect_check MCP tool — verify model representativeness against code reality."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import yaml


async def check_representativeness(repo_path: str, model_yaml: str) -> dict[str, Any]:
    """Check how well an architecture model represents the actual codebase.

    Supports three modes:
    - Hierarchical (config): uses pre-existing fblock_dict from config
    - Hierarchical (auto): generates F-blocks from module grouping when no config exists
    - Flat: fallback when neither hierarchical path is available

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

        # Parse the model via temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(model_yaml)
            tmp_path = f.name

        try:
            model = load_model(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        # Try hierarchical mode (config-based)
        output = _try_hierarchical(path, model)
        if output is None:
            # Try auto-F-block hierarchical mode
            output = _try_auto_hierarchical(path, model)
        if output is None:
            # Fall back to flat mode
            manifest = generate_manifest(path)
            result = _compute(model, manifest.modules, manifest.interfaces)
            output = {
                "mode": "flat",
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


def _try_hierarchical(path: Path, root_model) -> dict[str, Any] | None:
    """Attempt hierarchical check if recursive manifests are available via config."""
    try:
        from architecture_model.manifest.recursive import generate_recursive_manifests
        from architecture_model.core.representativeness import compute_hierarchical_representativeness
        from architecture_model.config.loader import get_config

        config = get_config(path)
        if not config.fblock_dict or len(config.fblock_dict) < 2:
            return None

        recursive_manifests = generate_recursive_manifests(path)
        if not recursive_manifests:
            return None

        result = compute_hierarchical_representativeness(
            root_model, {}, recursive_manifests
        )

        return _format_hierarchical_output(result)

    except Exception:
        return None


def _try_auto_hierarchical(path: Path, root_model) -> dict[str, Any] | None:
    """Attempt hierarchical check using auto-generated F-blocks from module grouping."""
    try:
        from architecture_model.manifest.generator import generate_manifest
        from architecture_model.manifest.grouping import group_modules, auto_fblocks
        from architecture_model.manifest.recursive import generate_recursive_manifests
        from architecture_model.core.representativeness import compute_hierarchical_representativeness

        manifest = generate_manifest(path)
        groups = group_modules(manifest.modules, manifest.interfaces)
        fblock_config = auto_fblocks(groups)

        if not fblock_config or len(fblock_config) < 2:
            return None

        recursive_manifests = generate_recursive_manifests(path, fblock_override=fblock_config)
        if not recursive_manifests:
            return None

        result = compute_hierarchical_representativeness(
            root_model, {}, recursive_manifests
        )

        output = _format_hierarchical_output(result)
        output["mode"] = "hierarchical_auto"
        output["fblock_count"] = len(fblock_config)
        return output

    except Exception:
        return None


def _format_hierarchical_output(result) -> dict[str, Any]:
    """Format a hierarchical representativeness result into output dict."""
    output: dict[str, Any] = {
        "mode": "hierarchical",
        "root": {
            "file_coverage": round(result.root.file_coverage, 1),
            "relationship_accuracy": round(result.root.relationship_accuracy, 1),
            "boundary_coherence": round(result.root.boundary_coherence, 1),
            "overall": round(result.root.overall, 1),
        },
        "blocks": {},
        "overall": round(result.overall, 1),
        "uncovered_files": result.root.uncovered_files,
        "unverified_relationships": result.root.unverified_relationships,
        "low_coherence_components": result.root.low_coherence_components,
    }

    for block_id, block_result in result.blocks.items():
        output["blocks"][block_id] = {
            "file_coverage": round(block_result.file_coverage, 1),
            "relationship_accuracy": round(block_result.relationship_accuracy, 1),
            "boundary_coherence": round(block_result.boundary_coherence, 1),
            "overall": round(block_result.overall, 1),
        }

    return output
