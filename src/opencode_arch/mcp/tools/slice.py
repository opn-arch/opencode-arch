"""architect_slice MCP tool — compress repository context for LLM consumption."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def compute_adaptive_budget(module_count: int, base: int = 4000) -> int:
    """Scale token budget with repository size.
    
    Small repos (<=20 modules): base budget (4000 tokens)
    Medium repos: +200 tokens per 10 modules over 20
    Large repos: capped at 16000 tokens
    
    Examples:
        20 modules → 4000 tokens
        50 modules → 4600 tokens  
        100 modules → 5600 tokens
        161 modules → 6800 tokens
        500 modules → 16000 tokens (capped)
    """
    if module_count <= 20:
        return base
    extra = ((module_count - 20) // 10) * 200
    return min(base + extra, 16000)


async def slice_context(
    repo_path: str,
    focus: str = "all",
    budget: int = 0,
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

        # Adaptive budget: compute from repo size if not specified
        if budget <= 0:
            if model_file.exists():
                from architecture_model.core.parser import load_model
                model = load_model(model_file)
                file_count = sum(len(getattr(c, 'files', [])) for c in model.entities.components)
                budget = compute_adaptive_budget(file_count)
            else:
                from architecture_model.manifest.generator import generate_manifest
                manifest = generate_manifest(path)
                budget = compute_adaptive_budget(len(manifest.modules))

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

    # Try to include grouped component suggestions for richer context
    groups_info = []
    try:
        from architecture_model.manifest.grouping import group_modules
        groups = group_modules(manifest.modules, manifest.interfaces)
        groups_info = [
            {"name": g.name, "files": g.modules, "primary": g.primary_file}
            for g in groups
        ]
    except Exception:
        pass

    manifest_yaml = yaml.dump(manifest, default_flow_style=False, sort_keys=False)

    char_budget = budget * 4
    if len(manifest_yaml) > char_budget:
        summary: dict[str, Any] = {
            "project_root": manifest.get("project_root"),
            "metrics": manifest.get("metrics", {}),
            "module_count": len(manifest.get("modules", [])),
        }
        if groups_info:
            summary["suggested_components"] = groups_info
        else:
            summary["functional_blocks"] = {
                k: {"file_count": len(v.get("sub_functions", []))}
                for k, v in manifest.get("functional_blocks", {}).items()
            }
        if focus != "all":
            summary["focus"] = focus
        manifest_yaml = yaml.dump(summary, default_flow_style=False, sort_keys=False)

    return manifest_yaml[:char_budget]
