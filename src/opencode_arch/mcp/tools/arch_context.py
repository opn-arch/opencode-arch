"""G1 round-centric context-read MCP tools.

Four PURE-READ wrappers over the openAG kernel following the OCA envelope
convention. These expose the B-ROUND context surface — ready frontier,
owed promises, typed gaps, and entity-scoped slices — without mutating the
model.

The openAG model lives at ``<repo_path>/.architecture/model/`` as a
directory of ``*.v3.yaml`` fragments. Each tool loads that directory, builds
a :class:`ModelGraph`, and delegates to the kernel.
"""
from __future__ import annotations

from opencode_arch.mcp.envelope import tool_result
from opencode_arch.mcp.tools._observe import observe_tool_call
from opencode_arch.mcp.tools._openag_loader import build_graph, load_doc


@tool_result
async def arch_frontier(repo_path: str) -> dict:
    """Return the ready-promise frontier (node ids) for the round."""
    with observe_tool_call(repo_path, "arch_frontier"):
        doc = load_doc(repo_path)
        g = build_graph(doc)

        from openag.kernel.readiness import ready_frontier

        return {"frontier": list(ready_frontier(g, set()))}


@tool_result
async def arch_owed(repo_path: str, node_id: str) -> dict:
    """Return valence-owed-but-absent attributes for an entity."""
    with observe_tool_call(repo_path, "arch_owed"):
        if not node_id or not isinstance(node_id, str):
            raise ValueError("node_id must be a non-empty string")
        doc = load_doc(repo_path)
        g = build_graph(doc)

        from openag.kernel.promise_engine import owed_promises_graph

        try:
            owed = owed_promises_graph(g, node_id)
        except KeyError:
            raise ValueError(f"unknown node_id: {node_id}")
        return {"owed": dict(owed)}


@tool_result
async def arch_gaps(repo_path: str, node_id: str) -> dict:
    """Return G-DELIVERY typed gaps for an entity."""
    with observe_tool_call(repo_path, "arch_gaps"):
        if not node_id or not isinstance(node_id, str):
            raise ValueError("node_id must be a non-empty string")
        doc = load_doc(repo_path)
        g = build_graph(doc)

        from openag.kernel.gate import emit_gaps_graph

        try:
            gaps = emit_gaps_graph(g, node_id)
        except KeyError:
            raise ValueError(f"unknown node_id: {node_id}")
        return {"gaps": list(gaps)}


@tool_result
async def arch_slice(repo_path: str, node_id: str) -> dict:
    """Return the entity-scoped sub-doc for an entity."""
    with observe_tool_call(repo_path, "arch_slice"):
        if not node_id or not isinstance(node_id, str):
            raise ValueError("node_id must be a non-empty string")
        doc = load_doc(repo_path)

        from openag.graph.slicer import slice_by_entity

        try:
            sub_doc = slice_by_entity(doc, node_id)
        except KeyError:
            raise ValueError(f"unknown node_id: {node_id}")
        return {"slice": sub_doc}
