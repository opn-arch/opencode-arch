"""arch_package_diff — native openAG generation-diff MCP tool.

Behavioral replacement for the legacy AMS architect_package_diff tool. Diffs two
published generation snapshots from the repo's GenerationStore via
openag.lifecycle.package.diff_generations_in_repo. No legacy architecture_model
dependency; reads published generations, not the model dir.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_package_diff(
    repo_path: str = "", gen_a: str = "", gen_b: str = ""
) -> dict:
    """Diff two published openAG generation snapshots."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    from openag.lifecycle.package import diff_generations_in_repo

    return diff_generations_in_repo(repo_path, gen_a, gen_b)
