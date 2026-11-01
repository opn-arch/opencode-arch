"""arch_health — B-ROUND health-projection context-read MCP tool.

A PURE-READ wrapper over the openAG kernel health projection following the
OCA envelope convention. Surfaces per-node health (with flags) when a
``node_id`` is given, or the graph-wide health roll-up otherwise.

The openAG model lives at ``<repo_path>/.architecture/model/`` as a
directory of ``*.v3.yaml`` fragments. Observations are read from
``<repo_path>/.architecture/observations.jsonl`` (empty when absent).
"""
from __future__ import annotations

from opencode_arch.mcp.envelope import resolve_repo, tool_result
from opencode_arch.mcp._arch_tool import arch_tool
from opencode_arch.mcp.tools._openag_loader import build_graph, load_doc


@arch_tool
async def arch_health(repo_path: str, node_id: str | None = None) -> dict:
    """Return per-node (with flags) or graph-wide health projection."""
    # Validate node_id up front (mirrors arch_context.py), but keep the
    # None fast-path: a None node_id is the valid graph-wide case.
    if node_id is not None and (not node_id or not isinstance(node_id, str)):
        raise ValueError("node_id must be a non-empty string")

    doc = load_doc(repo_path)
    g = build_graph(doc)

    from openag.kernel.health import graph_health, node_health
    from openag.observe import journal

    observations = journal.read(resolve_repo(repo_path))

    if node_id is None:
        return graph_health(g, observations)

    try:
        return node_health(g, node_id, observations)
    except KeyError:
        raise ValueError(f"unknown node_id: {node_id}")
