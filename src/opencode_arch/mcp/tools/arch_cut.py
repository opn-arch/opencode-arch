"""G3 cut tools: ``arch_propose_cut``, ``arch_score_cut``,
``arch_allocate_contract``.

``arch_propose_cut`` applies a partition-refinement proposal through the
openAG gated-write path. On a gate or conservation failure it returns a
soft verdict (``{"ok": False, "rejections": [...]}``) and NEVER mutates —
the B★ file-conservation safety property. The other two tools are pure
reads: ``arch_score_cut`` scores a candidate cut of a ground-graph slice
and ``arch_allocate_contract`` wraps the A2 assume-guarantee down-law.

Imports of ``openag`` are lazy so this module stays importable without
the dependency present.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json

from opencode_arch.mcp.envelope import tool_result
from opencode_arch.mcp._arch_tool import arch_tool
from opencode_arch.mcp.tools._openag_loader import build_graph, load_doc


@arch_tool
async def arch_propose_cut(repo_path: str, node_id: str, proposal: dict) -> dict:
    """Apply a partition-refinement proposal via the gated-write path.

    Returns a digest of the applied doc on success, or a sorted list of
    rejection strings on a gate/conservation failure (without mutating).
    """
    if not isinstance(node_id, str) or not node_id.strip():
        raise ValueError("node_id must be a non-empty string")
    if not isinstance(proposal, dict):
        raise ValueError("proposal must be a dict")

    doc = load_doc(repo_path)
    g = build_graph(doc)

    from openag.llm.proposal import proposal_from_dict

    parsed = proposal_from_dict(
        proposal, task_class="grow.decompose", prompt_digest="arch_propose_cut"
    )

    from openag.kernel.round import _split

    try:
        new_g = _split(g, parsed)
    except ValueError as exc:
        msg = str(exc)
        if msg.startswith("invalid proposal: "):
            remainder = msg[len("invalid proposal: ") :]
            rejections = remainder.split("; ")
        else:
            rejections = [f"conservation: {msg}"]
        return {"ok": False, "rejections": sorted(rejections)}

    applied = new_g.to_doc()
    digest = hashlib.sha256(
        json.dumps(applied, sort_keys=True, default=str).encode()
    ).hexdigest()
    return {"digest": digest, "node_id": node_id}


@tool_result
async def arch_score_cut(
    nodes: list[str], edges: list[list[str]], cells: list[list[str]]
) -> dict:
    """Score a candidate cut of a ground-graph slice (pure read)."""
    from openag.graph.ground import GroundGraph
    from openag.graph.cut_score import cut, score_cut

    gg = GroundGraph(
        nodes=tuple(nodes),
        edges=tuple(tuple(e) for e in edges),
    )
    c = cut(*[set(cell) for cell in cells])
    return {"score": float(score_cut(gg, c))}


@tool_result
async def arch_allocate_contract(interface_cut: dict) -> dict:
    """Allocate producer/consumer child contracts (A2 down-law, pure)."""
    from openag.kernel.contracts import allocate_contract

    try:
        producer, consumer = allocate_contract(interface_cut)
    except KeyError as exc:
        raise ValueError(f"malformed interface_cut: missing {exc}")

    return {
        "producer": dataclasses.asdict(producer),
        "consumer": dataclasses.asdict(consumer),
    }
