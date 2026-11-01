"""arch_require — native openAG requirement-capture MCP tool.

Behavioral replacement for the legacy AMS architect_require tool. Appends a
MoSCoW-prioritized functional requirement to the repo's requirements ledger via
openag.compliance.requirements.capture_requirement. No legacy architecture_model dependency.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_require(
    repo_path: str = "",
    requirement: str = "",
    component_id: str = "",
    priority: str = "must",
    context: str = "",
) -> dict:
    """Capture a MoSCoW-prioritized functional requirement for the repo."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    from openag.compliance.requirements import capture_requirement
    return capture_requirement(
        repo_path,
        requirement,
        component_id=component_id,
        priority=priority,
        context=context,
    )
