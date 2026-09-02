"""architect_check MCP tool — verify model representativeness against code reality."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import yaml

from opencode_arch.mcp.quality import with_quality


@with_quality
async def check_representativeness(repo_path: str, model_yaml: str = "") -> dict[str, Any]:
    """Check how well an architecture model represents the actual codebase.

    Supports three modes:
    - Hierarchical (config): uses pre-existing source_block_dict from config
    - Hierarchical (auto): generates F-blocks from module grouping when no config exists
    - Flat: fallback when neither hierarchical path is available

    Args:
        repo_path: Absolute path to the repository root.
        model_yaml: The architecture model YAML to evaluate.
            If empty, reads from {repo_path}/.architecture-model.yaml.

    Returns:
        Dict with scores, details, and suggested improvements.
    """
    path = Path(repo_path)
    if not path.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}

    try:
        from architecture_model.manifest.generator import generate_manifest
        from architecture_model.core.parser import load_model
        from architecture_model.core.representativeness import (
            compute_representativeness as _compute,
        )

        # C1: Read from disk if model_yaml is empty/looks like a file path
        if not model_yaml or not model_yaml.strip():
            model_file = path / ".architecture-model.yaml"
            if model_file.exists():
                model = load_model(model_file)
            else:
                return {
                    "error": f"No model found at {model_file}. Run architect_extract first, or pass model_yaml inline."
                }
        else:
            # Check if it looks like a file path
            stripped = model_yaml.strip()
            if (
                not stripped.startswith(("{", "[", "-", "#"))
                and "\n" not in stripped
                and (
                    stripped.startswith("/")
                    or stripped.startswith("~")
                    or stripped.endswith(".yaml")
                    or stripped.endswith(".yml")
                )
            ):
                candidate = Path(stripped).expanduser()
                if candidate.exists():
                    model = load_model(candidate)
                else:
                    return {
                        "error": f"'{stripped}' looks like a file path but doesn't exist. Pass inline YAML or leave empty to read from .architecture-model.yaml."
                    }
            else:
                # Parse inline YAML via temp file
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
        from architecture_model.core.representativeness import (
            compute_hierarchical_representativeness,
        )
        from architecture_model.config.loader import get_config

        config = get_config(path)
        if not config.source_block_dict or len(config.source_block_dict) < 2:
            return None

        recursive_manifests = generate_recursive_manifests(path)
        if not recursive_manifests:
            return None

        sub_models, hierarchy_issues = _resolve_sub_models(path, root_model)
        result = compute_hierarchical_representativeness(
            root_model, sub_models, recursive_manifests
        )

        return _format_hierarchical_output(result, hierarchy_issues)

    except Exception:
        return None


def _try_auto_hierarchical(path: Path, root_model) -> dict[str, Any] | None:
    """Attempt hierarchical check using auto-generated F-blocks from module grouping."""
    try:
        from architecture_model.manifest.generator import generate_manifest
        from architecture_model.manifest.grouping import group_modules, auto_source_blocks
        from architecture_model.manifest.recursive import generate_recursive_manifests
        from architecture_model.core.representativeness import (
            compute_hierarchical_representativeness,
        )

        manifest = generate_manifest(path)
        groups = group_modules(manifest.modules, manifest.interfaces)
        source_block_config = auto_source_blocks(groups)

        if not source_block_config or len(source_block_config) < 2:
            return None

        recursive_manifests = generate_recursive_manifests(
            path, source_block_override=source_block_config
        )
        if not recursive_manifests:
            return None

        sub_models, hierarchy_issues = _resolve_sub_models(path, root_model)
        result = compute_hierarchical_representativeness(
            root_model, sub_models, recursive_manifests
        )

        output = _format_hierarchical_output(result, hierarchy_issues)
        output["mode"] = "hierarchical_auto"
        output["source_block_count"] = len(source_block_config)
        return output

    except Exception:
        return None


def _resolve_sub_models(path: Path, root_model) -> tuple[dict[str, Any], list[str]]:
    """Safely load descendants and index them by their declared source block."""
    from architecture_model.core.hierarchy import load_model_hierarchy

    models, issues = load_model_hierarchy(root_model, path)
    loaded_by_path = {
        Path(model._source_path).resolve(): model
        for model in models[1:]
        if getattr(model, "_source_path", None)
    }
    sub_models: dict[str, Any] = {}
    root = path.resolve()

    for parent in models:
        parent_path = Path(
            getattr(parent, "_source_path", root / ".architecture-model.yaml")
        ).resolve()
        for system in parent.entities.systems:
            if not system.sub_model_ref or not system.source_block:
                continue
            local_candidate = (parent_path.parent / system.sub_model_ref).resolve()
            root_candidate = (root / system.sub_model_ref).resolve()
            candidate = local_candidate if local_candidate.is_file() else root_candidate
            child = loaded_by_path.get(candidate)
            if child is not None:
                sub_models[system.source_block] = child

    return sub_models, issues


def _format_hierarchical_output(
    result, hierarchy_issues: list[str] | None = None
) -> dict[str, Any]:
    """Format a hierarchical representativeness result into output dict."""
    hierarchy_issues = hierarchy_issues or []
    overall = min(result.overall, 75.0) if hierarchy_issues else result.overall
    output: dict[str, Any] = {
        "mode": "hierarchical",
        "root": {
            "file_coverage": round(result.root.file_coverage, 1),
            "relationship_accuracy": round(result.root.relationship_accuracy, 1),
            "boundary_coherence": round(result.root.boundary_coherence, 1),
            "overall": round(result.root.overall, 1),
        },
        "blocks": {},
        "overall": round(overall, 1),
        "hierarchy_issues": hierarchy_issues,
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
