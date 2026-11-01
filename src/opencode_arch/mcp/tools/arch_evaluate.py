"""arch_evaluate — native workspace-health MCP tool over openAG.

Behavioral replacement for the legacy AMS architect_evaluate tool. Loads the
openAG model graph (repo's merged model dir), scans the repo source into a
ground graph, and returns coverage + health + promise rollup + requirement
count via openag.kernel.evaluate.evaluate_workspace. No legacy
architecture_model dependency.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_evaluate(repo_path: str = "") -> dict:
    """Health check: model coverage, health score, promise rollup, requirements."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)  # NOT_FOUND on missing repo, same as arch_check
    from openag.kernel.evaluate import evaluate_workspace

    return evaluate_workspace(repo_path)
