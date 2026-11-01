"""arch_flags — B-ROUND proprioceptive anomaly-surface context-read MCP tool.

A PURE-READ wrapper over the openAG kernel's ``audit_observations`` following
the OCA envelope convention. Surfaces anomaly flags workspace-wide, or filtered
to a single ``node_id``.

The openAG model lives at ``<repo_path>/.architecture/model/`` as a
directory of ``*.v3.yaml`` fragments. Observations are read from
``<repo_path>/.architecture/observations.jsonl`` (empty when absent).
"""
from __future__ import annotations

import dataclasses

from opencode_arch.mcp.envelope import resolve_repo, tool_result
from opencode_arch.mcp._arch_tool import arch_tool
from opencode_arch.mcp.tools._openag_loader import build_graph, load_doc


@arch_tool
async def arch_flags(repo_path: str, node_id: str | None = None) -> dict:
    """Return proprioceptive anomaly flags (workspace-wide or node-filtered)."""
    # Validate node_id up front (mirrors arch_health.py), but keep the
    # None fast-path: a None node_id is the valid workspace-wide case.
    if node_id is not None and (not node_id or not isinstance(node_id, str)):
        raise ValueError("node_id must be a non-empty string")

    doc = load_doc(repo_path)
    g = build_graph(doc)

    from openag.observe import journal
    from openag.observe.audit import audit_observations

    observations = journal.read(resolve_repo(repo_path))
    flags = audit_observations(g, observations)

    if node_id is not None:
        try:
            g.node(node_id)
        except KeyError:
            raise ValueError(f"unknown node_id: {node_id}")
        flags = [f for f in flags if f.component_id == node_id]

    return {"flags": [dataclasses.asdict(f) for f in flags]}
