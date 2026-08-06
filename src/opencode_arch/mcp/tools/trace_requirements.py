"""architect_trace_requirements MCP tool — trace requirements to functions."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from opencode_arch.mcp.quality import with_quality
from opencode_arch.requirements.parser import parse_requirements_doc
from opencode_arch.requirements.llm_extractor import extract_requirements_llm
from opencode_arch.requirements.retroactive import derive_requirements_retroactive
from opencode_arch.requirements.matcher import match_functions_to_requirements


@with_quality
async def trace_requirements(
    repo_path: str,
    model_yaml: str = "",
    requirements_doc: str = "",
    _runner=None,
    _cache=None,
) -> dict:
    """Trace requirements to functions.

    If requirements_doc provided: parse structurally, fall back to LLM for freeform.
    If no requirements_doc: use retroactive derivation from model.
    Then match functions to requirements.
    Output: .architecture-models/requirements-trace.json
    """
    path = Path(repo_path)
    if not path.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}

    # Load model YAML if not provided
    if not model_yaml:
        model_file = path / ".architecture-model.yaml"
        if model_file.exists():
            model_yaml = model_file.read_text()

    # Create runner if not injected
    if _runner is None:
        from opencode_arch.runner.opencode import OpencodeRunner
        _runner = OpencodeRunner()

    # Step 1: Extract requirements
    requirements = []
    extraction_mode = "none"

    if requirements_doc:
        doc_path = Path(requirements_doc)
        if not doc_path.is_absolute():
            doc_path = path / doc_path
        if not doc_path.exists():
            return {"error": f"Requirements doc not found: {requirements_doc}"}

        # Try structural parsing first
        requirements = parse_requirements_doc(doc_path)
        extraction_mode = "structural"

        # Fall back to LLM if structural found nothing
        if not requirements:
            requirements = await extract_requirements_llm(
                doc_path, _runner, cache=_cache, repo_path=repo_path,
            )
            extraction_mode = "llm"
    else:
        # Retroactive: derive from model
        if not model_yaml:
            return {"error": "No requirements doc and no model available for retroactive derivation"}
        requirements = await derive_requirements_retroactive(
            model_yaml, _runner, cache=_cache, repo_path=repo_path,
        )
        extraction_mode = "retroactive"

    # Step 2: Match functions to requirements
    matches = []
    if requirements and model_yaml:
        matches = await match_functions_to_requirements(
            requirements, model_yaml, _runner, cache=_cache, repo_path=repo_path,
        )

    # Build result
    result = {
        "extraction_mode": extraction_mode,
        "requirements_count": len(requirements),
        "matches_count": len(matches),
        "requirements": [asdict(r) for r in requirements],
        "matches": [asdict(m) for m in matches],
    }

    # Write output
    out_dir = path / ".architecture-models"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "requirements-trace.json").write_text(json.dumps(result, indent=2))

    return result
