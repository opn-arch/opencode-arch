"""arch_stats — native openAG telemetry/rollup aggregation MCP tool.

Behavioral replacement for the legacy AMS architect_stats tool. Aggregates
per-tool invocation telemetry plus an optional model promise rollup via
openag.mining.stats.aggregate_stats. No legacy architecture_model dependency.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_stats(repo_path: str = "", tool_filter: str = "") -> dict:
    """Aggregate per-tool telemetry and optional model rollup for the repo."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    from openag.mining.stats import aggregate_stats
    return aggregate_stats(repo_path, tool_filter=tool_filter)
