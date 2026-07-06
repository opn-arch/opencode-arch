"""Bench command - benchmark extraction on multiple repos."""
from __future__ import annotations

from typing import Any

from opencode_arch.runner.base import RunnerBackend
from opencode_arch.cli.extract import run_extract


async def run_bench(
    repos: list[str],
    runner: RunnerBackend,
    budget: int = 4000,
    target_score: int = 80,
) -> list[dict[str, Any]]:
    """Run extraction benchmark on multiple repositories."""
    results = []
    for repo_path in repos:
        result = await run_extract(
            repo_path=repo_path, runner=runner,
            budget=budget, target_score=target_score,
        )
        result["repo"] = repo_path
        results.append(result)
    return results
