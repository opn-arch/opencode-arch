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
    return min(base + extra, 16000)


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

    # Help/introspect mode: return valid focus values and capabilities
    if focus in ("help", "introspect", "?"):
        return _help_text(path)

    # Schema mode: return dataclass definitions for named types
    if focus.startswith("schema:"):
        type_name = focus[7:].strip()
        return _schema_for_type(path, type_name)

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
        if focus != "all":
            if (path / ".architecture" / "requirements.yaml").exists():
                result = _append_requirements_context(path, focus, result)
            elif (path / ".architecture" / "derived_requirements.yaml").exists():
                result = _append_derived_requirements_context(path, focus, result)

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
    from architecture_model.core.slicer import slice_by_entity, slice_by_layer

    model_path = project_root / ".architecture-model.yaml"
    model = load_model(model_path)

    # Entity-focus form: focus="entity(<id>)" — Phase 3 Task 19.
    # Route through slice_by_entity so the returned context includes the entity,
    # its transitive `contains` descendants, and its 1-hop neighborhood only.
    if focus.startswith("entity(") and focus.endswith(")"):
        entity_id = focus[len("entity(") : -1].strip()
        if entity_id:
            try:
                sliced = slice_by_entity(model, entity_id=entity_id)
                return format_model_context(sliced, max_tokens=budget, detail_level=detail)
            except KeyError:
                # Unknown entity id — fall through to full-model formatting.
                return format_model_context(model, max_tokens=budget, detail_level=detail)

    # Try to include regen readiness grade in header
    try:
        from architecture_model.core.regen_readiness import compute_regen_readiness

        regen = compute_regen_readiness(model)
        regen_header = f"# Regen: {regen.grade} ({regen.overall:.0f}%)\n\n"
    except Exception:
        regen_header = ""

    if focus == "all":
        base = regen_header + format_model_context(model, max_tokens=budget, detail_level=detail)
        # For SoS models (has systems but no components with files), enrich with sub-model data
        has_file_detail = any(comp.files for comp in (model.entities.components or []))
        if not has_file_detail and (model.entities.systems or []):
            enrichment = _enrich_sos_with_files(project_root, budget)
            if enrichment:
                base += enrichment
        # Append test files section if available
        all_model_files = set()
        for comp in model.entities.components or []:
            all_model_files.update(str(f) for f in (comp.files or []))
        test_section = _get_test_files_section(project_root, all_model_files, budget * 2)
        if test_section:
            base += test_section
        conv_section = _get_convention_hints(project_root)
        if conv_section:
            base += conv_section
        return base
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
        # Try as system name (for SoS models) — check sub-models
        sub_model_dirs = [
            project_root / ".architecture-models",
            project_root / ".architecture" / ".architecture-models",
        ]
        for smd in sub_model_dirs:
            if not smd.exists():
                continue
            # Try exact match or slug match
            for subdir in smd.iterdir():
                if not subdir.is_dir():
                    continue
                if subdir.name == focus or focus in subdir.name:
                    sub_path = subdir / ".architecture-model.yaml"
                    if sub_path.exists():
                        sub_model = load_model(sub_path)
                        return format_model_context(
                            sub_model, max_tokens=budget, detail_level=detail
                        )

        try:
            sliced = slice_by_layer(model, layer_id=focus)
            return format_model_context(sliced, max_tokens=budget, detail_level=detail)
        except (KeyError, ValueError):
            return format_model_context(model, max_tokens=budget, detail_level=detail)


def _enrich_sos_with_files(project_root: Path, budget: int) -> str:
    """For System-of-Systems models, append component→file mappings from sub-models.

    This bridges the gap between the abstract SoS view (systems + relationships)
    and the concrete file-level detail an AI needs for impact analysis.
    Also includes import dependencies for change propagation reasoning.
    """
    from architecture_model.core.parser import load_model

    sub_model_dirs = [
        project_root / ".architecture-models",
        project_root / ".architecture" / ".architecture-models",
    ]

    lines = ["\n\n## Component → File Mapping (from sub-models)"]
    char_budget = budget * 2  # Allow extra chars for file detail
    used = 0
    all_files: set[str] = set()

    for smd in sub_model_dirs:
        if not smd.exists():
            continue
        for subdir in sorted(smd.iterdir()):
            if not subdir.is_dir():
                continue
            sub_path = subdir / ".architecture-model.yaml"
            if not sub_path.exists():
                continue
            try:
                sm = load_model(sub_path)
                comps = sm.entities.components or []
                if not comps:
                    continue
                sys_line = f"\n### {subdir.name.replace('-', ' ').title()}"
                lines.append(sys_line)
                used += len(sys_line)
                for c in comps:
                    if not c.files:
                        continue
                    file_strs = [str(f) for f in c.files]
                    all_files.update(file_strs)
                    comp_line = f"  **{c.name}**: {', '.join(file_strs)}"
                    if used + len(comp_line) > char_budget:
                        lines.append("  ... (truncated)")
                        break
                    lines.append(comp_line)
                    used += len(comp_line)
            except Exception:
                continue

    # Add import graph if available (from pipeline cache)
    import_section = _get_import_graph_section(project_root, all_files, char_budget - used)
    if import_section:
        lines.append(import_section)

    if len(lines) <= 1:
        return ""
    return "\n".join(lines)


def _get_import_graph_section(project_root: Path, model_files: set[str], char_budget: int) -> str:
    """Generate import dependency section from cached pipeline data or quick AST scan."""
    import json as _json

    # Try to load from pipeline cache
    cache_locations = [
        project_root / ".benchmark-cache",
        project_root / ".architecture",
    ]

    import_graph: dict[str, list[str]] = {}
    for cache_dir in cache_locations:
        if not cache_dir.exists():
            continue
        for f in cache_dir.iterdir():
            if f.name.endswith(".import_graph.json"):
                try:
                    data = _json.loads(f.read_text())
                    import_graph = data.get("forward", {})
                    break
                except Exception:
                    continue
        if import_graph:
            break

    if not import_graph or not model_files:
        return ""

    lines = ["\n\n## Import Dependencies (for change propagation)"]
    lines.append("(file → files it imports; use to predict cascading changes)")
    used = len("\n".join(lines))

    shown = 0
    for src in sorted(import_graph.keys()):
        if src not in model_files:
            continue
        targets = [t for t in import_graph[src] if t in model_files]
        if not targets:
            continue
        line = f"  {src} → {', '.join(sorted(targets)[:5])}"
        if used + len(line) > char_budget:
            lines.append(
                f"  ... (+{sum(1 for s in import_graph if s in model_files) - shown} more)"
            )
            break
        lines.append(line)
        used += len(line)
        shown += 1
        if shown >= 50:
            lines.append(
                f"  ... (+{sum(1 for s in import_graph if s in model_files) - shown} more)"
            )
            break

    if shown == 0:
        return ""
    return "\n".join(lines)


def _get_test_files_section(project_root: Path, focus_files: set[str], char_budget: int) -> str:
    """Generate related test files section from test_map.json or component_test_map.json."""
    import json as _json

    # Try to load test map
    test_map: dict[str, list[str]] = {}
    for loc in [
        project_root / ".architecture" / "test_map.json",
        project_root / ".architecture" / "component_test_map.json",
    ]:
        if loc.exists():
            try:
                test_map = _json.loads(loc.read_text())
                break
            except Exception:
                continue

    if not test_map:
        return ""

    # Collect test files relevant to the focused source files
    relevant_tests: dict[str, list[str]] = {}  # test_file → [source files it tests]
    for source_file in focus_files:
        tests = test_map.get(source_file, [])
        for t in tests:
            relevant_tests.setdefault(t, []).append(source_file)

    if not relevant_tests:
        return ""

    lines = ["\n\n## Related Test Files"]
    lines.append("(Files that import this component's source — likely need updating on changes)")
    used = len("\n".join(lines))

    # Sort by relevance (more source imports = more relevant)
    sorted_tests = sorted(relevant_tests.items(), key=lambda x: -len(x[1]))

    shown = 0
    for test_file, sources in sorted_tests:
        src_hint = sources[0] if len(sources) == 1 else f"{sources[0]} +{len(sources) - 1}"
        line = f"  - {test_file} (imports {src_hint})"
        if used + len(line) > char_budget:
            lines.append(f"  ... (+{len(sorted_tests) - shown} more)")
            break
        lines.append(line)
        used += len(line)
        shown += 1
        if shown >= 20:
            remaining = len(sorted_tests) - shown
            if remaining > 0:
                lines.append(f"  ... (+{remaining} more)")
            break

    if shown == 0:
        return ""
    return "\n".join(lines)


def _get_convention_hints(project_root: Path) -> str:
    """Detect and return project test/doc conventions from test_map patterns."""
    import json as _json

    map_path = project_root / ".architecture" / "test_map.json"
    if not map_path.exists():
        return ""
    try:
        test_map = _json.loads(map_path.read_text())
    except Exception:
        return ""

    if not test_map:
        return ""

    # Analyze test file patterns
    all_tests = [t for tests in test_map.values() for t in tests]
    if not all_tests:
        return ""

    from collections import Counter

    patterns: Counter = Counter()
    for t in all_tests:
        parts = Path(t).parts
        if len(parts) > 1 and "_tests" in parts[-2]:
            patterns["mirror ({module}_tests/)"] += 1
        elif Path(t).stem.startswith("test_"):
            patterns["prefix (test_{module}.py)"] += 1
        else:
            patterns["other"] += 1

    dominant = patterns.most_common(1)[0][0] if patterns else "unknown"

    # Check for docs directory
    docs_dirs = []
    for d in ["docs", "doc", "documentation"]:
        if (project_root / d).is_dir():
            docs_dirs.append(d + "/")

    lines = ["\n\n## Project Conventions"]
    lines.append(f"  - Test pattern: {dominant}")
    if docs_dirs:
        lines.append(f"  - Documentation: {', '.join(docs_dirs)}")

    return "\n".join(lines)


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


def _append_derived_requirements_context(project_root: Path, focus: str, result: str) -> str:
    """Include auto-derived requirements when slicing a specific component/block."""
    try:
        req_file = project_root / ".architecture" / "derived_requirements.yaml"
        data = yaml.safe_load(req_file.read_text()) or {}
        requirements = data.get("derived_requirements", [])
        if not requirements:
            return result

        # Filter by component_id match
        focus_lower = focus.lower()
        matched = [r for r in requirements if r.get("component_id", "").lower() == focus_lower]
        if not matched:
            # Try matching focus in the requirement name or source_file
            matched = [
                r
                for r in requirements
                if focus_lower in r.get("name", "").lower()
                or focus_lower in r.get("source_file", "").lower()
            ]
        if not matched:
            # Show top must-priority requirements
            matched = [r for r in requirements if r.get("priority") == "must"][:8]

        if matched:
            req_section = "\n\n---\n# Derived Requirements\n"
            for r in matched[:12]:
                priority = r.get("priority", "should")
                category = r.get("category", "")
                req_section += f"- [{priority}|{category}] {r.get('name', 'untitled')}"
                if r.get("component_id"):
                    req_section += f" → {r['component_id']}"
                req_section += "\n"
            if len(matched) > 12:
                req_section += f"  ... +{len(matched) - 12} more\n"
            result += req_section

    except Exception:
        pass
    return result


def _help_text(project_root: Path) -> str:
    """Return introspection info: valid focus values, modes, and capabilities."""
    model_path = project_root / ".architecture-model.yaml"
    lines = [
        "# architect_slice — Help / Introspect",
        "",
        "## Valid focus values:",
        "  - `all` — full model context (default)",
        "  - `help` or `introspect` or `?` — this help text",
        "  - `schema:<TypeName>` — dataclass field definitions for a named type",
    ]

    if model_path.exists():
        model_data = yaml.safe_load(model_path.read_text()) or {}
        components = model_data.get("entities", {}).get("components", [])

        # Source blocks
        blocks = sorted(set(c.get("source_block", "") for c in components if c.get("source_block")))
        if blocks:
            lines.append(f"  - Source blocks: {', '.join(blocks)}")

        # Component IDs
        comp_list = [f"{c['id']} ({c['name']})" for c in components]
        lines.append("  - Component IDs (use as focus):")
        for c in comp_list:
            lines.append(f"    - {c}")

        lines.append("  - Artifact names:")
        artifacts = [
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
        ]
        for a in artifacts:
            lines.append(f"    - {a}")
    else:
        lines.append("  (no model found — run architect_pipeline first)")

    lines.extend(
        [
            "",
            "## Parameters:",
            "  - budget: Token budget (0=auto-calculate, max 64000)",
            "  - detail: minimal | standard | full",
            "",
            "## Compression thresholds:",
            f"  - <50x: good (78% pass rate)",
            f"  - 50-200x: warning (44-55% pass rate)",
            f"  - >200x: critical (19% pass rate) — use per-block slicing",
        ]
    )
    return "\n".join(lines)


def _schema_for_type(project_root: Path, type_name: str) -> str:
    """Return dataclass/class field definitions for a named type."""
    import ast as _ast

    results = []
    src_dir = project_root / "src"
    if not src_dir.exists():
        src_dir = project_root

    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            tree = _ast.parse(py_file.read_text())
        except Exception:
            continue

        for node in _ast.walk(tree):
            if isinstance(node, _ast.ClassDef) and node.name == type_name:
                # Extract source lines
                source = py_file.read_text().splitlines()
                start = node.lineno - 1
                end = node.end_lineno or (start + 20)
                class_source = "\n".join(source[start:end])
                rel_path = py_file.relative_to(project_root)
                results.append(f"# {rel_path}:{node.lineno}\n{class_source}")

    if not results:
        return f"Type '{type_name}' not found in {project_root.name}. Try: architect_scan to see available types."

    return f"# Schema for {type_name}\n\n" + "\n\n---\n\n".join(results)
