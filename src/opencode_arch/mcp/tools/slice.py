"""architect_slice MCP tool — compress repository context for LLM consumption."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


async def slice_context(
    repo_path: str,
    focus: str = "all",
    budget: int = 4000,
    detail: str = "standard",
) -> str:
    """Generate an optimized context slice from a repository.

    This is the core token-arbitrage function. It compresses a full repository
    into a dense, structured context string within the token budget.

    If an .architecture-model.yaml exists, uses the model + slicer + formatter.
    Otherwise, falls back to manifest-based context.

    Args:
        repo_path: Absolute path to the repository root.
        focus: Focus scope - "all", an F-block ID (e.g. "F1"), a layer name,
               or an artifact name (e.g. "icd", "requirements-analysis").
        budget: Maximum token budget (1 token ~ 4 chars).
        detail: Detail level - "minimal", "standard", or "full".

    Returns:
        Formatted context string within budget, or error message.
    """
    path = Path(repo_path)
    if not path.exists():
        return f"Error: Repository path does not exist: {repo_path}"

    try:
        model_file = path / ".architecture-model.yaml"

        if model_file.exists():
            result = _slice_from_model(path, focus, budget, detail)
        else:
            result = _slice_from_manifest(path, focus, budget)

        try:
            from opencode_arch.telemetry.collector import drain_and_store
            drain_and_store(tool="architect_slice", repo=path.name)
        except Exception:
            pass
        return result

    except Exception as e:
        return f"Error during context slicing: {e}"


def _slice_from_model(project_root: Path, focus: str, budget: int, detail: str) -> str:
    """Slice context using the architecture model (rich path)."""
    from architecture_model.core.parser import load_model
    from opencode_arch.context import (
        format_model_context,
        format_fblock_context,
        format_artifact_context,
    )
    from architecture_model.core.slicer import slice_by_layer

    model_path = project_root / ".architecture-model.yaml"
    model = load_model(model_path)

    if focus == "all":
        return format_model_context(model, max_tokens=budget, detail_level=detail)
    elif focus.startswith("F") and focus[1:].isdigit():
        return format_fblock_context(model, f_block=focus, max_tokens=budget, project_root=project_root)
    elif focus in (
        "functional-architecture", "logical-architecture", "use-cases",
        "icd", "requirements-analysis", "operations-manual", "conops",
        "testing", "deployment-guide", "data-dictionary", "readme",
    ):
        return format_artifact_context(model, artifact_name=focus, max_tokens=budget)
    else:
        try:
            sliced = slice_by_layer(model, layer_id=focus)
            return format_model_context(sliced, max_tokens=budget, detail_level=detail)
        except (KeyError, ValueError):
            return format_model_context(model, max_tokens=budget, detail_level=detail)


def _slice_from_manifest(project_root: Path, focus: str, budget: int) -> str:
    """Slice context using manifest only (no architecture model yet)."""
    from architecture_model.manifest.generator import generate_manifest

    manifest = generate_manifest(project_root)

    manifest_yaml = yaml.dump(manifest, default_flow_style=False, sort_keys=False)

    char_budget = budget * 4
    if len(manifest_yaml) > char_budget:
        summary = {
            "project_root": manifest.get("project_root"),
            "metrics": manifest.get("metrics", {}),
            "functional_blocks": {
                k: {"file_count": len(v.get("sub_functions", []))}
                for k, v in manifest.get("functional_blocks", {}).items()
            },
            "module_count": len(manifest.get("modules", [])),
        }
        if focus != "all":
            summary["focus"] = focus
        manifest_yaml = yaml.dump(summary, default_flow_style=False, sort_keys=False)

    return manifest_yaml[:char_budget]
