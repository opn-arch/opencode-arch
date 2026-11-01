"""arch_package_children_add — native openAG child-refs ledger MCP tool.

Behavioral replacement for the legacy AMS architect_package_children_add tool.
Appends ``(child_ref, revision)`` to the repo's deterministic child-refs ledger
via openag.lifecycle.children.add_child. openAG-shaped & IDEMPOTENT: re-adding
an identical pair is a no-op (added=False), not an error. No legacy AMS
dependency.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_package_children_add(
    repo_path: str = "",
    child_ref: str = "",
    revision: str = "",
) -> dict:
    """Append a child package ref to the repo's deterministic child-refs ledger."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    from openag.lifecycle.children import add_child

    return add_child(repo_path, child_ref, revision=revision)
