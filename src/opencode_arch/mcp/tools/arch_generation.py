"""G5 identity/generation tools: ``arch_bind`` and ``arch_commit_generation``.

The synchronic B-ROUND fixpoint is stateless across runs; diachronic identity
continuity lives in the :class:`~openag.kernel.generations.GenerationStore`
under ``<repo>/.architecture/generations/``.

* ``arch_commit_generation`` records an identity projection of the current
  model — plus its graph-wide ``graph_health`` projection — as the next
  monotone 7-digit generation.
* ``arch_bind`` runs the θ-crosswalk (``kernel.identity.crosswalk``) of the
  latest recorded generation onto the current model, surfacing the per-entity
  bind/ambiguous/new verdict, orphans, and the Layer-2 identity gaps.

Imports of ``openag`` are lazy so this module stays importable without the
dependency present.
"""
from __future__ import annotations

from opencode_arch.mcp.envelope import resolve_repo, tool_result
from opencode_arch.mcp.tools._generations import generation_store
from opencode_arch.mcp.tools._observe import observe_tool_call
from opencode_arch.mcp.tools._openag_loader import build_graph, load_doc


def _flatten_entities(doc: dict) -> list[dict]:
    """Flatten every entity (across all kinds) from an openAG doc."""
    entities = doc.get("entities") or {}
    return [e for items in entities.values() for e in (items or [])]


def _current_entities(repo_path: str) -> list[dict]:
    """Flatten every entity (across all kinds) from the merged openAG doc."""
    return _flatten_entities(load_doc(repo_path))


@tool_result
async def arch_bind(repo_path: str) -> dict:
    """θ-crosswalk the latest generation onto the current model (pure read).

    Returns the per-entity identity verdict plus orphans, identity gaps, the
    ambiguous-band sublist, and the sticky (bound) ids.
    """
    from openag.kernel.identity import crosswalk, identity_gaps

    with observe_tool_call(repo_path, "arch_bind"):
        current = _current_entities(repo_path)
        store = generation_store(repo_path)
        latest = store.latest()
        old_entities = latest["entities"] if latest else []
        sticky = store.sticky_anchors()

        result = crosswalk(old_entities, current, sticky_anchors=sticky)
        gaps = identity_gaps(result)

        return {
            "entries": [
                {
                    "new_id": e.new_id,
                    "bound_to": e.bound_to,
                    "band": e.band,
                    "score": e.score,
                }
                for e in result.entries
            ],
            "orphans": result.orphans,
            "gaps": gaps,
            "ambiguous": [g for g in gaps if g["gap_type"] == "gap:ambiguous-identity"],
            "sticky": [e.new_id for e in result.entries if e.band == "bind"],
        }


@tool_result
async def arch_commit_generation(repo_path: str) -> dict:
    """Record the current model as the next monotone generation.

    Returns the new ``gen_id`` (7-digit string), the committed entity count,
    and the graph-wide ``graph_health`` projection recorded alongside it.
    """
    with observe_tool_call(repo_path, "arch_commit_generation"):
        doc = load_doc(repo_path)
        current = _flatten_entities(doc)
        g = build_graph(doc)

        from openag.kernel.health import graph_health
        from openag.observe import journal

        observations = journal.read(resolve_repo(repo_path))
        health = graph_health(g, observations)

        store = generation_store(repo_path)
        gen_id = store.record(current, health=health)
        return {"gen_id": gen_id, "entity_count": len(current), "health": health}
