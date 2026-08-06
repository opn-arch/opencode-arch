"""LLM-assisted requirement extraction from freeform documents."""
from __future__ import annotations

import json
import re
import hashlib
from pathlib import Path

from opencode_arch.llm.cache import LLMCache, cached_llm_call, hash_content
from opencode_arch.llm.prompts.requirements import (
    REQUIREMENTS_EXTRACT_TEMPLATE,
    REQUIREMENTS_EXTRACT_VERSION,
)
from opencode_arch.requirements.parser import ExtractedRequirement


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM output, handling markdown code fences."""
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


async def extract_requirements_llm(
    doc_path: Path,
    runner,
    cache: LLMCache | None = None,
    repo_path: str = "",
) -> list[ExtractedRequirement]:
    """Use LLM to segment freeform prose into requirements."""
    content = doc_path.read_text()
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

    prompt = REQUIREMENTS_EXTRACT_TEMPLATE.format(doc_content=content)
    result = await cached_llm_call(
        runner,
        prompt,
        hash_content(content),
        hash_content(REQUIREMENTS_EXTRACT_VERSION),
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
            source_doc=str(doc_path),
            source_anchor=r.get("anchor", ""),
            content_hash=content_hash,
            extraction_method="llm",
        ))

    return results
