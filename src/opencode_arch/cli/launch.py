"""Interactive launch — architecture-aware development session.

Pre-flight: scan, slice, persist, update CONTEXT.md, then exec opencode.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Markers for the architecture section in CONTEXT.md
CONTEXT_START = "<!-- opencode-arch:start -->"
CONTEXT_END = "<!-- opencode-arch:end -->"

# Minimal opencode.json template
OPENCODE_JSON_TEMPLATE = {
    "name": "opencode-arch",
    "version": "1.0.0",
    "description": "Architecture-aware development tools",
    "mcp": {
        "command": "python",
        "args": ["-m", "opencode_arch.mcp.server"],
        "tools": [
            {"name": "architect_scan", "description": "Scan repository AST to generate manifest"},
            {"name": "architect_slice", "description": "Get token-compressed architecture context"},
            {"name": "architect_validate", "description": "Validate architecture model (0-100)"},
            {"name": "architect_extract", "description": "Store validated architecture model"},
            {"name": "architect_generate", "description": "Run tests on generated code"},
            {"name": "architect_group", "description": "Auto-group modules into components"},
            {"name": "architect_check", "description": "Verify model representativeness"},
            {"name": "architect_require", "description": "Capture functional requirement"},
            {"name": "architect_feedback", "description": "Record feedback for training"},
        ],
    },
}


def run_launch(repo_path: str | None = None, skip_exec: bool = False) -> dict:
    """Run pre-flight checks and launch interactive OpenCode session.
    
    Args:
        repo_path: Target repository (default: current directory)
        skip_exec: If True, do pre-flight only without exec (for testing)
    
    Returns:
        Pre-flight results dict (only if skip_exec=True)
    """
    repo = Path(repo_path or ".").resolve()
    if not repo.is_dir():
        print(f"Error: {repo} is not a directory", file=sys.stderr)
        sys.exit(1)

    start = time.time()
    results = {"repo": str(repo), "steps": []}

    # Step 1: Scan
    manifest = None
    try:
        from architecture_model.manifest.generator import generate_manifest
        manifest = generate_manifest(repo)
        results["modules"] = len(manifest.modules)
        results["interfaces"] = len(manifest.interfaces)
        results["steps"].append("scan")
        _status(f"Scanned {len(manifest.modules)} modules")
    except Exception as exc:
        _warn(f"Scan skipped: {exc}")

    # Step 2: Load or bootstrap model
    model = None
    model_path = repo / ".architecture-model.yaml"
    try:
        if model_path.exists():
            from architecture_model.core.parser import load_model
            model = load_model(model_path)
            _status(f"Model loaded: {len(model.entities.components)} components")
        elif manifest:
            from architecture_model.manifest.grouping import create_components_from_manifest
            from architecture_model.core.types import ArchitectureModel, Entities, ModelMeta
            from architecture_model.orchestration.auto_enrich import enrich_from_manifest
            
            components = create_components_from_manifest(manifest)
            model = ArchitectureModel(
                meta=ModelMeta(project=repo.name, schema_version="1.3"),
                entities=Entities(components=components),
                relationships=[],
            )
            enrich_from_manifest(model, manifest)
            _status(f"Bootstrapped model: {len(components)} components")
        results["steps"].append("model")
    except Exception as exc:
        _warn(f"Model load/bootstrap skipped: {exc}")

    # Step 3: Slice context
    context_slice = ""
    if model and manifest:
        try:
            from architecture_model.integrations.llm_context import format_model_context
            from opencode_arch.mcp.tools.slice import compute_adaptive_budget
            adaptive_budget = compute_adaptive_budget(len(manifest.modules))
            context_slice = format_model_context(model, budget=adaptive_budget, detail="standard")
            results["context_tokens"] = len(context_slice) // 4  # rough estimate
            results["steps"].append("slice")
        except Exception:
            # Fallback: build a compact summary
            try:
                comps = model.entities.components
                lines = [f"## Architecture: {len(comps)} components"]
                for c in comps[:20]:
                    files = ", ".join(getattr(c, 'files', [])[:3])
                    lines.append(f"- **{c.name}** ({c.id}): {files}")
                context_slice = "\n".join(lines)
                results["steps"].append("slice_fallback")
            except Exception:
                pass

    # Step 4: Compute representativeness
    rep = None
    if model and manifest:
        try:
            from architecture_model.core.representativeness import compute_representativeness
            rep = compute_representativeness(model, manifest.modules, manifest.interfaces)
            results["representativeness"] = rep.overall
            results["steps"].append("repr")
            _status(f"Representativeness: {rep.overall:.1f}%")
        except Exception as exc:
            _warn(f"Representativeness skipped: {exc}")

    # Step 5: Persist to .architecture/
    if model and manifest:
        try:
            from architecture_model.persistence.store import save_project
            save_project(repo, model, manifest, representativeness=rep)
            results["steps"].append("persist")
        except Exception as exc:
            _warn(f"Persistence skipped: {exc}")

    # Step 6: Update CONTEXT.md
    _update_context_md(repo, model, context_slice, rep, manifest)
    results["steps"].append("context_md")

    # Step 7: Ensure opencode.json
    _ensure_opencode_json(repo)
    results["steps"].append("opencode_json")

    elapsed = time.time() - start
    results["elapsed_s"] = round(elapsed, 2)
    _status(f"Ready ({elapsed:.1f}s)")

    if skip_exec:
        return results

    # Step 8: Exec opencode
    opencode_bin = shutil.which("opencode")
    if not opencode_bin:
        print("Error: 'opencode' not found in PATH. Install OpenCode first.", file=sys.stderr)
        print("  See: https://opencode.ai", file=sys.stderr)
        sys.exit(1)

    os.chdir(repo)
    os.execvp(opencode_bin, [opencode_bin])


def _update_context_md(
    repo: Path,
    model,
    context_slice: str,
    rep,
    manifest,
) -> None:
    """Update CONTEXT.md with architecture section between markers."""
    context_path = repo / "CONTEXT.md"
    
    # Build architecture section
    lines = [CONTEXT_START]
    lines.append("# Architecture (auto-managed by opencode-arch)")
    lines.append("")
    
    if model:
        comp_count = len(model.entities.components)
        rel_count = len(model.relationships) if model.relationships else 0
        lines.append(f"**Model:** {comp_count} components | {rel_count} relationships")
    
    if rep:
        lines.append(f"**Score:** {rep.overall:.1f}% "
                     f"(FC={rep.file_coverage:.0f}% RA={rep.relationship_accuracy:.0f}% "
                     f"BC={rep.boundary_coherence:.0f}% BV={rep.behavioral_coverage:.0f}%)")
    
    if manifest:
        lines.append(f"**Codebase:** {len(manifest.modules)} modules | "
                     f"{len(manifest.interfaces)} import edges")
    
    # Requirements count
    req_path = repo / ".architecture" / "requirements.yaml"
    if req_path.exists():
        try:
            import yaml
            reqs = yaml.safe_load(req_path.read_text()) or {}
            req_list = reqs.get("requirements", [])
            lines.append(f"**Requirements:** {len(req_list)} tracked")
        except Exception:
            pass
    
    lines.append("")
    
    if context_slice:
        lines.append("## Component Map")
        lines.append("")
        lines.append(context_slice)
        lines.append("")
    
    lines.append("## Development Guidelines")
    lines.append("")
    lines.append("- Use `architect_slice` for focused context on specific components")
    lines.append("- Use `architect_check` after significant changes to verify model accuracy")
    lines.append("- Use `architect_require` to capture functional requirements from discussion")
    lines.append("- Use `architect_feedback` to record corrections or rate tool quality")
    lines.append("- Components are auto-grouped by import affinity — respect boundaries")
    lines.append(CONTEXT_END)
    
    arch_section = "\n".join(lines) + "\n"
    
    # Read existing CONTEXT.md
    if context_path.exists():
        content = context_path.read_text()
        # Replace existing section or append
        if CONTEXT_START in content:
            # Replace between markers
            before = content[:content.index(CONTEXT_START)]
            after_marker = content[content.index(CONTEXT_END) + len(CONTEXT_END):]
            content = before + arch_section + after_marker
        else:
            # Append at end
            if not content.endswith("\n"):
                content += "\n"
            content += "\n" + arch_section
    else:
        content = arch_section
    
    context_path.write_text(content)


def _ensure_opencode_json(repo: Path) -> None:
    """Ensure opencode.json exists in repo for MCP tool registration."""
    opencode_json_path = repo / "opencode.json"
    if not opencode_json_path.exists():
        opencode_json_path.write_text(
            json.dumps(OPENCODE_JSON_TEMPLATE, indent=2) + "\n"
        )


def _status(msg: str) -> None:
    """Print a status line."""
    print(f"  \u2713 {msg}", file=sys.stderr)


def _warn(msg: str) -> None:
    """Print a warning line."""
    print(f"  ! {msg}", file=sys.stderr)
