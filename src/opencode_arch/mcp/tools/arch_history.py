"""arch_history — B-ROUND diachronic generation-ledger read MCP tool.

A PURE-READ surface over the health-enriched
:class:`~openag.kernel.generations.GenerationStore` under
``<repo>/.architecture/generations/`` (written by ``arch_commit_generation``).
History is model-independent, so this tool does NOT load the openAG model or
build the graph. It exposes three mutually-exclusive modes, dispatched in
strict precedence order:

1. diff — both ``gen_a`` and ``gen_b`` given: the semantic diff between them.
2. trajectory — ``node_id`` given: a node's verdict history across generations.
3. timeline — no args: a concise per-generation rollup.
"""
from __future__ import annotations

from opencode_arch.mcp.envelope import tool_result
from opencode_arch.mcp.tools._generations import generation_store
from opencode_arch.mcp.tools._observe import observe_tool_call


def _timeline_entry(gen: dict) -> dict:
    """A concise rollup of one generation for the timeline view."""
    health = gen.get("health") or {}
    return {
        "gen_id": gen.get("gen_id"),
        "entity_count": len(gen.get("entities") or []),
        "verdict_counts": health.get("verdict_counts", {}),
        "silence_index": health.get("silence_index"),
        "flag_rollup": health.get("flag_rollup", {}),
    }


@tool_result
async def arch_history(
    repo_path: str,
    node_id: str | None = None,
    gen_a: str | None = None,
    gen_b: str | None = None,
) -> dict:
    """Return the generation timeline, a node trajectory, or a generation diff."""
    with observe_tool_call(repo_path, "arch_history"):
        # Up-front argument validation (mirrors arch_health.py's node_id guard).
        if node_id is not None and (not node_id or not isinstance(node_id, str)):
            raise ValueError("node_id must be a non-empty string")
        if gen_a is not None and (not gen_a or not isinstance(gen_a, str)):
            raise ValueError("gen_a must be a non-empty string")
        if gen_b is not None and (not gen_b or not isinstance(gen_b, str)):
            raise ValueError("gen_b must be a non-empty string")

        # Exactly-one-gen guard: a diff needs both endpoints.
        if (gen_a is None) != (gen_b is None):
            raise ValueError("both gen_a and gen_b are required for a generation diff")

        store = generation_store(repo_path)

        # 1. diff mode — both gen ids given (node_id ignored).
        if gen_a is not None and gen_b is not None:
            try:
                diff = store.diff_generations(gen_a, gen_b)
            except KeyError as exc:
                raise ValueError(f"unknown generation: {exc}")
            return {"mode": "diff", "gen_a": gen_a, "gen_b": gen_b, "diff": diff}

        # 2. trajectory mode — a node's verdict history (empty list is not error).
        if node_id is not None:
            return {
                "mode": "trajectory",
                "node_id": node_id,
                "history": store.node_history(node_id),
            }

        # 3. timeline mode — concise per-generation rollup.
        return {
            "mode": "timeline",
            "generations": [_timeline_entry(gen) for gen in store.all()],
        }
