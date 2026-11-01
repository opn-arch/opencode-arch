"""arch_package_load — native openAG generation-load MCP tool.

Behavioral replacement for the legacy AMS architect_package_load tool. Reads a
published generation snapshot from the repo's GenerationStore via
openag.lifecycle.package.load_generation. No legacy architecture_model
dependency; reads published generations, not the model dir.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_package_load(repo_path: str = "", gen_id: str = "") -> dict:
    """Load a published openAG generation snapshot (latest when gen_id empty)."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    from openag.lifecycle.package import load_generation

    return load_generation(repo_path, gen_id or None)
