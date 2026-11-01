"""arch_view_render — native openAG viewer-HTML render MCP tool.

Behavioral replacement for the legacy AMS architect_view_render tool. Renders
the repo's openAG model doc into the self-contained viewer HTML document via
openag.lifecycle.views.render_view (project -> bake -> digest). The model doc
is either supplied inline as ``model_yaml`` or loaded from the repo's openAG
model dir. No legacy architecture_model dependency. Pure read — no generation
is published.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_view_render(
    repo_path: str = "",
    model_yaml: str = "",
) -> dict:
    """Render an openAG model doc into the self-contained viewer HTML."""
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

    from openag.lifecycle.views import render_view

    return render_view(doc)
