"""architect_slice MCP tool — compress repository context for LLM consumption."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


# Simple in-process cache for slicing results (cleared on process restart)
_slice_cache: dict[tuple, str] = {}
_CACHE_MAX = 32


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
    return min(base + extra, 64000)


# Compression ratio thresholds (from telemetry analysis of 389 regen outcomes)
# <2x: 78% pass | 2-10x: 69% | 10-50x: 55% | 50-200x: 44% | >200x: 19%
COMPRESSION_WARN_THRESHOLD = 50  # warn above this
COMPRESSION_CRITICAL_THRESHOLD = 200  # strongly recommend per-block above this


def _estimate_source_size(path: Path) -> int:
    """Estimate total source code size in chars (quick heuristic)."""
    total = 0
    for ext in ("*.py", "*.ts", "*.js", "*.go", "*.rs", "*.java"):
        for f in path.rglob(ext):
            # Skip vendor, node_modules, .git
            parts = f.parts
            if any(
                p in parts for p in ("vendor", "_vendor", "node_modules", ".git", "__pycache__")
            ):
                continue
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return total


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
        focus: Focus scope - "all", an source-block ID (e.g. "F1"), a layer name,
               or an artifact name (e.g. "icd", "requirements-analysis").
        budget: Maximum token budget (1 token ~ 4 chars).
        detail: Detail level - "minimal", "standard", or "full".

    Returns:
        Formatted context string within budget, or error message.
    """
    path = Path(repo_path)
    if not path.exists():
        return f"Error: Repository path does not exist: {repo_path}"

    # Cache check
    cache_key = (repo_path, focus, budget, detail)
    if cache_key in _slice_cache:
        return _slice_cache[cache_key]

    try:
        model_file = path / ".architecture-model.yaml"

        # Adaptive budget: compute from repo size if not specified
        if budget <= 0:
            if model_file.exists():
                from architecture_model.core.parser import load_model

                model = load_model(model_file)
                file_count = sum(len(getattr(c, "files", [])) for c in model.entities.components)
                budget = compute_adaptive_budget(file_count)
            else:
                from architecture_model.manifest.generator import generate_manifest

                manifest = generate_manifest(path)
                budget = compute_adaptive_budget(len(manifest.modules))

            # Secondary check: ensure compression ratio stays below 50x
            source_size = _estimate_source_size(path)
            min_budget_for_50x = source_size // (50 * 4)  # 50x compression, 4 chars/token
            if min_budget_for_50x > budget:
                budget = min(min_budget_for_50x, 64000)  # cap at 64K tokens

        if model_file.exists():
            result = _slice_from_model(path, focus, budget, detail)
        else:
            result = _slice_from_manifest(path, focus, budget)
            # SL6: Prepend guidance when no model exists
            result = _no_model_guidance(path) + "\n---\n\n" + result

        # Compression ratio guard: warn if context is dangerously compressed
        source_size = _estimate_source_size(path)
        char_budget = budget * 4
        if source_size > 0 and char_budget > 0:
            ratio = source_size / char_budget
            if ratio > COMPRESSION_CRITICAL_THRESHOLD:
                warning = (
                    f"# COMPRESSION WARNING: {ratio:.0f}x compression detected!\n"
                    f"# Source: {source_size // 1024}KB compressed into {char_budget // 1024}KB context.\n"
                    f"# At >200x compression, regeneration pass rate drops to ~19%.\n"
                    f"# RECOMMENDATION: Use focused slicing (architect_slice with focus='F1', 'F2', etc.)\n"
                    f"# to slice per-block. Available source-blocks can be found via architect_scan.\n\n"
                )
                result = warning + result
            elif ratio > COMPRESSION_WARN_THRESHOLD:
                warning = (
                    f"# NOTE: {ratio:.0f}x compression ratio (>50x reduces pass rate).\n"
                    f"# Consider per-block slicing for better regeneration outcomes.\n\n"
                )
                result = warning + result

        # Append linked requirements context when focusing on a component/block
        if focus != "all" and (path / ".architecture" / "requirements.yaml").exists():
            result = _append_requirements_context(path, focus, result)

        try:
            from opencode_arch.telemetry.collector import drain_and_store

            drain_and_store(tool="architect_slice", repo=path.name)
        except Exception:
            pass

        # Cache result (bounded LRU)
        if len(_slice_cache) >= _CACHE_MAX:
            # Remove oldest entry
            oldest_key = next(iter(_slice_cache))
            del _slice_cache[oldest_key]
        _slice_cache[cache_key] = result

        return result

    except Exception as e:
        return f"Error during context slicing: {e}"


def _slice_from_model(project_root: Path, focus: str, budget: int, detail: str) -> str:
    """Slice context using the architecture model (rich path)."""
    from architecture_model.core.parser import load_model
    from opencode_arch.context import (
        format_model_context,
        format_source_block_context,
        format_artifact_context,
    )
    from architecture_model.core.slicer import slice_by_layer

    model_path = project_root / ".architecture-model.yaml"
    model = load_model(model_path)

    if focus == "all":
        return format_model_context(model, max_tokens=budget, detail_level=detail)
    elif (focus.startswith("F") or focus.startswith("S")) and focus[1:].isdigit():
        # Check for sub-model first
        sub_model_path = project_root / ".architecture-models" / focus / ".architecture-model.yaml"
        if sub_model_path.exists():
            sub_model = load_model(sub_model_path)
            return format_model_context(sub_model, max_tokens=budget, detail_level=detail)
        # Complexity-proportional budget: complex blocks get more tokens
        block_budget = _compute_block_budget(model, focus, budget)
        return format_source_block_context(
            model, source_block=focus, max_tokens=block_budget, project_root=project_root
        )
    elif focus in (
        "functional-architecture",
        "logical-architecture",
        "use-cases",
        "icd",
        "requirements-analysis",
        "operations-manual",
        "conops",
        "testing",
        "deployment-guide",
        "data-dictionary",
        "readme",
    ):
        return format_artifact_context(model, artifact_name=focus, max_tokens=budget)
    else:
        try:
            sliced = slice_by_layer(model, layer_id=focus)
            return format_model_context(sliced, max_tokens=budget, detail_level=detail)
        except (KeyError, ValueError):
            return format_model_context(model, max_tokens=budget, detail_level=detail)


def _compute_block_budget(model: Any, source_block: str, total_budget: int) -> int:
    """Allocate budget proportionally to block complexity.

    Complex blocks (many signatures/files) get more tokens.
    Simple blocks get the minimum needed.
    Telemetry: <10 signatures reliably converge; complex blocks need 2-3x more context.
    """
    components = [
        c for c in model.entities.components if getattr(c, "source_block", "") == source_block
    ]
    if not components:
        # No source_block match — give full budget
        return total_budget

    # Complexity = total signatures + total files
    sig_count = sum(len(getattr(c, "signatures", [])) for c in components)
    file_count = sum(len(getattr(c, "files", [])) for c in components)
    complexity = sig_count + file_count

    # Simple (< 10): base budget, Complex (10-30): 1.5x, Very complex (>30): 2x
    if complexity < 10:
        return min(total_budget, 4000)
    elif complexity < 30:
        return min(int(total_budget * 1.5), 8000)
    else:
        return min(total_budget * 2, 16000)


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
            {"name": g.name, "files": g.modules, "primary": g.primary_file} for g in groups
        ]
    except Exception:
        pass

    manifest_dict = manifest.to_dict() if hasattr(manifest, "to_dict") else manifest
    manifest_yaml = yaml.dump(manifest_dict, default_flow_style=False, sort_keys=False)

    char_budget = budget * 4
    if len(manifest_yaml) > char_budget:
        summary: dict[str, Any] = {
            "project_root": manifest_dict.get("project_root"),
            "metrics": manifest_dict.get("metrics", {}),
            "module_count": len(manifest_dict.get("modules", [])),
        }
        if groups_info:
            summary["suggested_components"] = groups_info
        else:
            summary["functional_blocks"] = {
                k: {"file_count": len(v.get("sub_functions", []))}
                for k, v in manifest_dict.get("functional_blocks", {}).items()
            }
        if focus != "all":
            summary["focus"] = focus
        manifest_yaml = yaml.dump(summary, default_flow_style=False, sort_keys=False)

    return manifest_yaml[:char_budget]


def _no_model_guidance(project_root: Path) -> str:
    """SL6: Return helpful guidance when no architecture model exists."""
    return (
        f"# No architecture model found at {project_root}/.architecture-model.yaml\n\n"
        "To create one, follow this workflow:\n"
        "1. `architect_scan(repo_path)` — scan the codebase AST\n"
        "2. `architect_group(repo_path)` — discover component boundaries\n"
        "3. Build a YAML model from the scan + group output\n"
        "4. `architect_extract(repo_path, model_yaml)` — store and validate\n"
        "5. `architect_slice(repo_path)` — now you can slice the model\n\n"
        "Or use `architect_pipeline(repo_path, stage='observe')` for automated extraction.\n"
    )


def _append_requirements_context(project_root: Path, focus: str, result: str) -> str:
    """Include linked requirements when slicing a specific component/block."""
    try:
        req_file = project_root / ".architecture" / "requirements.yaml"
        data = yaml.safe_load(req_file.read_text()) or {}
        requirements = data.get("requirements", [])
        if not requirements:
            return result

        # Filter: if focus is a component ID or block ID, match linked requirements
        focus_lower = focus.lower()
        matched = [
            r
            for r in requirements
            if (
                r.get("component_id", "").lower() == focus_lower
                or focus_lower in r.get("title", "").lower()
                or focus_lower in r.get("description", "").lower()
            )
        ]
        if not matched:
            # Show all requirements if focusing on a block (they may relate)
            matched = requirements[:10]  # cap at 10

        if matched:
            req_section = "\n\n---\n# Linked Requirements\n"
            for r in matched:
                priority = r.get("priority", "should")
                req_section += f"- [{priority.upper()}] {r.get('title', 'untitled')}"
                if r.get("component_id"):
                    req_section += f" (component: {r['component_id']})"
                req_section += "\n"
                if r.get("description"):
                    req_section += f"  {r['description'][:200]}\n"
            result += req_section

    except Exception:
        pass
    return result
