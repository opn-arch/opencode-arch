"""arch_slice_materialize — native openAG entity-scoped slice MCP tool.

Behavioral replacement for the legacy AMS architect_slice_materialize tool.
Materializes an entity-scoped slice (scope chain, in-scope subtree + context
neighborhood, promise rollup) over the repo's openAG model doc via
openag.lifecycle.slices.materialize_slice. The model doc is either supplied
inline as ``model_yaml`` or loaded from the repo's openAG model dir. No legacy
architecture_model dependency. Pure read — no generation is published.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_slice_materialize(
    repo_path: str = "",
    entity_id: str = "",
    model_yaml: str = "",
) -> dict:
    """Materialize an entity-scoped slice of an openAG model doc."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    if model_yaml:
        import yaml

        doc = yaml.safe_load(model_yaml)
        if doc is None or not isinstance(doc, dict):
            raise ValueError("model_yaml must parse to a dict")
    else:
        from opencode_arch.mcp.tools._openag_loader import load_doc

        doc = load_doc(repo_path)

    if not doc.get("entities"):
        raise ValueError("model doc has no entities")

    from openag.lifecycle.slices import materialize_slice

    return materialize_slice(doc, entity_id)
