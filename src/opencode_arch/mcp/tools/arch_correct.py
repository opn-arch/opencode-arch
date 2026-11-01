"""arch_correct — native openAG structured-correction MCP tool.

Behavioral replacement for the legacy AMS architect_correct tool. Appends a
structured architecture-model correction to the repo's corrections ledger via
openag.mining.corrections.store_correction. No legacy architecture_model dependency.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_correct(
    repo_path: str = "",
    correction_type: str = "",
    target: str = "",
    reason: str = "",
    suggestion: dict | None = None,
) -> dict:
    """Store a structured architecture-model correction for the repo."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    from openag.mining.corrections import store_correction
    return store_correction(
        repo_path,
        correction_type,
        target,
        reason,
        suggestion=suggestion,
    )
