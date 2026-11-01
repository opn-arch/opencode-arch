"""arch_package_stale — native openAG path-index staleness MCP tool.

Behavioral replacement for the legacy AMS architect_package_stale tool. Given a
set of changed file paths, returns the model entities whose ``files`` lists
intersect a changed path, anchored to the latest recorded generation. The model
doc is supplied inline as ``model_yaml`` or loaded from the repo's openAG model
dir. No legacy AMS dependency. Pure read — no generation is published.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_package_stale(
    repo_path: str = "",
    changed_paths: list[str] | None = None,
    model_yaml: str = "",
) -> dict:
    """Return entities made stale by ``changed_paths``, anchored to the latest generation."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    if changed_paths is None:
        changed_paths = []

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

    from openag.kernel.generations import GenerationStore
    from openag.lifecycle import store_root
    from openag.lifecycle.staleness import stale_report

    latest = GenerationStore(store_root(repo_path)).latest()
    base_generation = latest.get("gen_id") if latest else None

    return stale_report(doc, changed_paths, base_generation=base_generation)
