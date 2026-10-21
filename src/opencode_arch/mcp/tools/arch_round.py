"""G2 round-execution MCP tool.

``arch_round`` runs the B-ROUND least-fixpoint over the openAG model,
either whole-graph or scoped to a single node's ``contains``-subtree.

The run is a PURE read of disk: :func:`openag.kernel.round.b_round`
mutates only the in-memory :class:`ModelGraph` and never writes back to
the model directory. With no provider it is pure-symbolic and
deterministic (temp-0 equivalent), so repeated calls yield a byte-stable
``grounded_digest``.

The openAG model lives at ``<repo_path>/.architecture/model/`` as a
directory of ``*.v3.yaml`` fragments.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from opencode_arch.mcp.envelope import resolve_repo, tool_result

_MODEL_REL = Path(".architecture") / "model"


def _load_doc(repo_path: str):
    """Resolve the repo + openAG model dir and return the merged doc.

    Raises:
        ValueError / FileNotFoundError / NotADirectoryError: from
            ``resolve_repo`` (repo-level validation).
        FileNotFoundError: when the openAG model dir is absent or empty.
    """
    repo = resolve_repo(repo_path)
    model_dir = repo / _MODEL_REL
    if not model_dir.is_dir():
        raise FileNotFoundError(f"openAG model dir not found: {model_dir}")
    if not any(model_dir.glob("*.v3.yaml")):
        raise FileNotFoundError(f"openAG model dir is empty: {model_dir}")

    from openag.model_io import load_model_dir

    return load_model_dir(str(model_dir))


def _owned_promise_ids(doc: dict, scope_ids: set[str]) -> set[str]:
    """Authored promise ids owned by entities whose id is in ``scope_ids``."""
    owned: set[str] = set()
    for group in (doc.get("entities") or {}).values():
        for e in group:
            if e.get("id") not in scope_ids:
                continue
            for p in (e.get("promises") or []):
                pid = p.get("id")
                if pid:
                    owned.add(pid)
    return owned


@tool_result
async def arch_round(repo_path: str, node_id: str | None = None) -> dict:
    """Run the B-ROUND least-fixpoint (whole-graph or node-scoped).

    When ``node_id`` is supplied, the reported grounded set is scoped to
    the authored promises owned by entities in that node's
    ``contains``-subtree. When ``node_id`` is ``None``, the full grounded
    set is reported.
    """
    if node_id is not None and (not node_id.strip() or not isinstance(node_id, str)):
        raise ValueError("node_id must be a non-empty string when provided")

    doc = _load_doc(repo_path)

    from openag.graph.model_graph import ModelGraph

    g = ModelGraph.from_doc(doc)

    from openag.kernel.round import b_round

    result = b_round(g)  # no provider → pure-symbolic, deterministic

    grounded = result["grounded"]

    if node_id is None:
        scoped_grounded = sorted(grounded)
    else:
        from openag.graph.slicer import slice_by_entity

        try:
            scope = slice_by_entity(doc, node_id)
        except KeyError:
            raise ValueError(f"unknown node_id: {node_id}")
        # ``nodes`` are dicts; the contains-subtree is the in-scope set
        # (includes the node itself). Neighbors carry in_scope=False.
        scope_ids = {
            n["id"]
            for n in scope["nodes"]
            if n.get("in_scope") and n.get("id")
        }
        owned = _owned_promise_ids(doc, scope_ids)
        scoped_grounded = sorted(set(grounded) & owned)

    grounded_digest = hashlib.sha256(
        json.dumps(sorted(scoped_grounded)).encode()
    ).hexdigest()

    return {
        "grounded_digest": grounded_digest,
        "grounded": scoped_grounded,
        "ungrounded": result["ungrounded"],
        "gaps": result["gaps"],
        "converged": result["converged"],
        "iterations": result["iterations"],
    }
