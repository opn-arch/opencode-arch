"""Extract command - full architecture extraction loop."""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from opencode_arch.runner.base import RunnerBackend
from opencode_arch.cli.prompts import EXTRACT_PROMPT


async def run_extract(
    repo_path: str,
    runner: RunnerBackend,
    budget: int = 4000,
    focus: str = "all",
    target_score: int = 80,
) -> dict[str, Any]:
    """Run the full extraction loop.

    1. Validates repo exists
    2. Calls runner with extraction prompt
    3. Parses YAML from output
    4. Validates and stores via tool APIs
    5. Returns metrics
    """
    path = Path(repo_path)
    if not path.exists():
        return {"success": False, "error": f"Path does not exist: {repo_path}"}

    start_time = time.time()

    prompt = EXTRACT_PROMPT.format(
        repo_path=str(path.resolve()),
        focus=focus,
        budget=budget,
        target_score=target_score,
    )

    result = await runner.run(prompt=prompt, repo_path=str(path))
    elapsed = time.time() - start_time

    if not result.success:
        return {
            "success": False,
            "error": f"Runner failed: {result.output[:500]}",
            "time_seconds": elapsed,
        }

    yaml_content = _extract_yaml_from_output(result.output)
    if not yaml_content:
        return {
            "success": False,
            "error": "No YAML model found in agent output",
            "time_seconds": elapsed,
        }

    from opencode_arch.mcp.tools.extract import store_extraction
    store_result = await store_extraction(
        repo_path=str(path),
        model_yaml=yaml_content,
        context_tokens=budget,
    )

    return {
        "success": store_result.get("stored", False),
        "score": store_result.get("score", 0),
        "tokens_used": budget,
        "time_seconds": elapsed,
        "iterations": 1,
        "issues": store_result.get("issues", []),
        "path": store_result.get("path", ""),
    }


def _extract_yaml_from_output(output: str) -> str | None:
    """Extract YAML content from agent output (between ```yaml fences)."""
    match = re.search(r"```ya?ml\s*\n(.*?)```", output, re.DOTALL)
    if match:
        return match.group(1).strip()

    match = re.search(r"```\s*\n(.*?)```", output, re.DOTALL)
    if match:
        content = match.group(1).strip()
        if "meta:" in content or "entities:" in content:
            return content

    match = re.search(r"(meta:\s*\n.*?)(?:\n\n|\Z)", output, re.DOTALL)
    if match:
        return match.group(1).strip()

    return None
