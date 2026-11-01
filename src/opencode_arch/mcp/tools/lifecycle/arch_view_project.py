"""arch_view_project — native openAG viewer-payload projection MCP tool.

Behavioral replacement for the legacy AMS architect_view_project tool.
Projects the repo's openAG model doc into a deterministic viewer payload via
openag.lifecycle.views.project_view, optionally scoped to one entity's
drill-down subgraph. The model doc is either supplied inline as ``model_yaml``
or loaded from the repo's openAG model dir. No legacy architecture_model
dependency. Pure read — no generation is published.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_view_project(
    repo_path: str = "",
    entity_id: str = "",
    model_yaml: str = "",
) -> dict:
    """Project an openAG model doc into a viewer payload view."""
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

    from openag.lifecycle.views import project_view

    return project_view(doc, entity_id)
