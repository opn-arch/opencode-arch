"""Function-Requirement matching using LLM."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

import yaml as _yaml_mod

from opencode_arch.llm.cache import LLMCache, cached_llm_call, hash_content
from opencode_arch.llm.prompts.matching import MATCHING_TEMPLATE, MATCHING_VERSION
from opencode_arch.requirements.parser import ExtractedRequirement


@dataclass
class RequirementMatch:
    function_id: str
    requirement_id: str
    confidence: float
    evidence: str
    extraction_method: str  # "llm_matched"


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM output."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except (json.JSONDecodeError, ValueError):
            pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except (json.JSONDecodeError, ValueError):
            pass
    return {"matches": []}


def _extract_functions_from_model(model_yaml: str) -> str:
    """Extract function/component info from model YAML for matching."""
    try:
        model = _yaml_mod.safe_load(model_yaml)
    except Exception:
        return "(no functions found)"

    lines = []
    entities = model.get("entities", {})
    for comp in entities.get("components", []):
        cid = comp.get("id", "")
        name = comp.get("name", "")
        lines.append(f"- {cid}: {name}")
    for cap in entities.get("capabilities", []):
        cid = cap.get("id", "")
        name = cap.get("name", "")
        lines.append(f"- {cid}: {name}")

    return "\n".join(lines) if lines else "(no functions found)"


async def match_functions_to_requirements(
    requirements: list[ExtractedRequirement],
    model_yaml: str,
    runner,
    cache: LLMCache | None = None,
    repo_path: str = "",
) -> list[RequirementMatch]:
    """Match functions to requirements using LLM with body_hints as evidence."""
    if not requirements:
        return []

    reqs_text = "\n".join(f"- {r.id}: {r.text}" for r in requirements)
    funcs_text = _extract_functions_from_model(model_yaml)

    prompt = MATCHING_TEMPLATE.format(
        requirements_text=reqs_text,
        functions_text=funcs_text,
    )

    combined_hash = hash_content(reqs_text + funcs_text)
    result = await cached_llm_call(
        runner,
        prompt,
        combined_hash,
        hash_content(MATCHING_VERSION),
        repo_path,
        cache=cache,
    )

    parsed = _extract_json(result.output)
    matches_raw = parsed.get("matches", [])

    results: list[RequirementMatch] = []
    for m in matches_raw:
        if not isinstance(m, dict):
            continue
        func_id = m.get("function_id", "")
        req_id = m.get("requirement_id", "")
        if not func_id or not req_id:
            continue
        results.append(RequirementMatch(
            function_id=func_id,
            requirement_id=req_id,
            confidence=float(m.get("confidence", 0.0)),
            evidence=m.get("evidence", ""),
            extraction_method="llm_matched",
        ))

    return results
