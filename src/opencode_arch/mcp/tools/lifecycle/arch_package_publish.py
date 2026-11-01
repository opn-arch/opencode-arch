"""arch_package_publish — native openAG generation-publish MCP tool.

Behavioral replacement for the legacy AMS architect_package_publish tool.
Flattens the repo's openAG model doc (or an inline ``model_yaml`` override) and
records it as the next generation snapshot via
openag.lifecycle.package.publish_generation. No legacy architecture_model
dependency.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_package_publish(
    repo_path: str = "",
    model_yaml: str = "",
    reason: str = "",
) -> dict:
    """Publish the repo's model as the next openAG generation snapshot."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    if model_yaml:
        import yaml

        doc = yaml.safe_load(model_yaml)
        if doc is None or not isinstance(doc, dict):
            raise ValueError("model_yaml did not parse to a dict")
    else:
        from opencode_arch.mcp.tools._openag_loader import load_doc

        doc = load_doc(repo_path)

    if not doc.get("entities"):
        raise ValueError("model doc has no entities")

    from openag.lifecycle.package import publish_generation

    return publish_generation(repo_path, doc, reason=reason)
