"""architect_llm_audit MCP tool — two-stage LLM functional-decomposition audit."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from opencode_arch.llm.cache import LLMCache, cached_llm_call, hash_content
from opencode_arch.llm.prompts.audit import (
    AUDIT_STAGE1_TEMPLATE,
    AUDIT_STAGE1_VERSION,
    AUDIT_STAGE2_TEMPLATE,
    AUDIT_STAGE2_VERSION,
)
from opencode_arch.mcp.quality import with_quality


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM output, handling markdown code fences."""
    # Try direct parse first
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass
    # Try extracting from code fence
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except (json.JSONDecodeError, ValueError):
            pass
    # Last resort: find first { ... }
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except (json.JSONDecodeError, ValueError):
            pass
    return {"parse_error": "Could not extract JSON from LLM output", "raw": text[:500]}


def _build_source_summary(repo_path: Path) -> str:
    """Build a compact source summary from Python files."""
    lines = []
    for py_file in sorted(repo_path.rglob("*.py")):
        if any(p in py_file.parts for p in ("__pycache__", ".venv", "node_modules", ".git")):
            continue
        rel = py_file.relative_to(repo_path)
        try:
            source = py_file.read_text(errors="ignore")
        except Exception:
            continue
        funcs = re.findall(r"^(?:async\s+)?def\s+(\w+)", source, re.MULTILINE)
        classes = re.findall(r"^class\s+(\w+)", source, re.MULTILINE)
        parts = [str(rel)]
        if classes:
            parts.append(f"classes: {', '.join(classes)}")
        if funcs:
            parts.append(f"functions: {', '.join(funcs)}")
        lines.append(" | ".join(parts))
    return "\n".join(lines) if lines else "(no Python files found)"


def _read_context(repo_path: Path) -> str:
    """Read CONTEXT.md or README.md from repo."""
    for name in ("CONTEXT.md", "README.md"):
        f = repo_path / name
        if f.exists():
            try:
                return f.read_text(errors="ignore")[:4000]
            except Exception:
                pass
    return "(no context file found)"


def _get_tool_decomposition(model: Any) -> tuple[str, float, str]:
    """Extract F-block decomposition info from model for stage 2."""
    blocks_info = []
    modularity = 0.0
    conductance_str = "N/A"

    try:
        from architecture_model.core.source_block_quality import compute_source_block_quality
        quality = compute_source_block_quality(model)
        modularity = quality.modularity
        conductance_str = json.dumps({b.block_id: round(b.conductance, 3) for b in quality.per_block})
    except Exception:
        pass

    if hasattr(model, "entities") and hasattr(model.entities, "components"):
        for comp in model.entities.components:
            blocks_info.append(f"- {comp.id}: {comp.name}")

    return "\n".join(blocks_info) if blocks_info else "(no components)", modularity, conductance_str


@with_quality
async def run_llm_audit(
    repo_path: str,
    model_yaml: str = "",
    _runner=None,
    _cache: LLMCache | None = None,
) -> dict[str, Any]:
    """Run two-stage LLM functional-decomposition audit."""
    path = Path(repo_path)
    if not path.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}

    # Load model
    model = None
    if model_yaml:
        yaml_str = model_yaml
    else:
        model_file = path / ".architecture-model.yaml"
        if model_file.exists():
            yaml_str = model_file.read_text()
        else:
            yaml_str = ""

    if yaml_str:
        try:
            from architecture_model.core.parser import parse_model
            model = parse_model(yaml_str)
        except Exception:
            pass

    # Build inputs
    source_summary = _build_source_summary(path)
    context_md = _read_context(path)
    content_hash = hash_content(source_summary)

    # Create runner if not injected
    if _runner is None:
        from opencode_arch.runner.opencode import OpencodeRunner
        _runner = OpencodeRunner()

    # Stage 1: Blind decomposition
    stage1_prompt = AUDIT_STAGE1_TEMPLATE.format(
        source_summary=source_summary,
        context_md=context_md,
    )
    stage1_result = await cached_llm_call(
        _runner,
        stage1_prompt,
        content_hash,
        hash_content("stage1:" + AUDIT_STAGE1_VERSION),
        repo_path,
        cache=_cache,
    )
    llm_decomposition = _extract_json(stage1_result.output)

    # Stage 2: Comparison
    tool_decomp_str = "(no model loaded)"
    modularity = 0.0
    conductance_str = "N/A"
    if model is not None:
        tool_decomp_str, modularity, conductance_str = _get_tool_decomposition(model)

    stage2_prompt = AUDIT_STAGE2_TEMPLATE.format(
        llm_decomposition=json.dumps(llm_decomposition, indent=2),
        tool_decomposition=tool_decomp_str,
        modularity=modularity,
        conductance=conductance_str,
    )
    stage2_result = await cached_llm_call(
        _runner,
        stage2_prompt,
        content_hash,
        hash_content("stage2:" + AUDIT_STAGE2_VERSION),
        repo_path,
        cache=_cache,
    )
    comparison = _extract_json(stage2_result.output)

    # Build result
    result = {
        "llm_decomposition": llm_decomposition,
        "comparison": comparison,
        "stage1_cached": stage1_result.cached,
        "stage2_cached": stage2_result.cached,
    }

    # Write output
    out_dir = path / ".architecture-models"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "llm-audit.json").write_text(json.dumps(result, indent=2))

    return result
