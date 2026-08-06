"""Retroactive requirement derivation from existing architecture models."""
from __future__ import annotations

import json
import re

from opencode_arch.llm.cache import LLMCache, cached_llm_call, hash_content
from opencode_arch.llm.prompts.requirements import (
    REQUIREMENTS_RETROACTIVE_TEMPLATE,
    REQUIREMENTS_RETROACTIVE_VERSION,
)
from opencode_arch.requirements.parser import ExtractedRequirement


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
    return {"requirements": []}


async def derive_requirements_retroactive(
    model_yaml: str,
    runner,
    cache: LLMCache | None = None,
    repo_path: str = "",
) -> list[ExtractedRequirement]:
    """Derive requirements from existing model artifacts when no requirements doc exists."""
    prompt = REQUIREMENTS_RETROACTIVE_TEMPLATE.format(model_yaml=model_yaml)
    result = await cached_llm_call(
        runner,
        prompt,
        hash_content(model_yaml),
        hash_content(REQUIREMENTS_RETROACTIVE_VERSION),
        repo_path,
        cache=cache,
    )

    parsed = _extract_json(result.output)
    reqs = parsed.get("requirements", [])

    results: list[ExtractedRequirement] = []
    for r in reqs:
        if not isinstance(r, dict):
            continue
        req_id = r.get("id", "")
        text = r.get("text", "")
        if not req_id or not text:
            continue
        results.append(ExtractedRequirement(
            id=req_id,
            text=text,
            source_doc="model",
            source_anchor=r.get("source", ""),
            content_hash=hash_content(model_yaml)[:16],
            extraction_method="retroactive",
        ))

    return results
