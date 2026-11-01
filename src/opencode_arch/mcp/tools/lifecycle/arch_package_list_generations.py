"""arch_package_list_generations — native openAG generation-list MCP tool.

Behavioral replacement for the legacy AMS architect_package_list_generations
tool. Enumerates published generation snapshots from the repo's GenerationStore
via openag.lifecycle.package.list_generations. No legacy architecture_model
dependency; reads published generations, not the model dir. An empty store is a
success (count 0), not an error.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_package_list_generations(repo_path: str = "") -> dict:
    """List published openAG generation snapshots in store order."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    from openag.lifecycle.package import list_generations

    return list_generations(repo_path)
