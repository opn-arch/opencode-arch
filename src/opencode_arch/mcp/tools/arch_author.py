"""arch_author — native openAG forward-authoring MCP tool.

Behavioral replacement for the legacy AMS architect_author tool. Parses a
requirements text block into a concept-phase openAG model doc via
openag.llm.author.author_from_requirements, builds the in-memory ModelGraph,
and records the resulting entities as a new generation in the repo's generation
store. No legacy architecture_model dependency.
"""
from __future__ import annotations

from pathlib import Path

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_author(repo_path: str = "", requirements_text: str = "") -> dict:
    """Forward-author a concept-phase model from requirements and record a generation."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    from openag.llm.author import author_from_requirements
    doc = author_from_requirements(requirements_text)

    from openag.graph.model_graph import ModelGraph
    g = ModelGraph.from_doc(doc)
    entities = g.entities_flat()

    from openag.kernel.generations import GenerationStore, rollup_of
    store = GenerationStore(root=str(Path(repo_path) / ".architecture" / "generations"))
    gen_id = store.record(entities, reason="authored from requirements", rollup=rollup_of(entities))

    caps = [e for e in entities if e.get("kind") == "Capability"]

    return {
        "gen_id": gen_id,
        "entity_count": len(entities),
        "capabilities": len(caps),
        "lifecycle_phase": "concept",
    }
