"""arch_group — native module-grouping MCP tool over openAG.

Behavioral replacement for the legacy AMS architect_group tool. Loads the
openAG model graph (inline model_yaml or the repo's merged model dir) and
projects its A1 containment partition into module groups via
openag.kernel.grouping.group_modules. No legacy architecture_model dependency.
"""
from __future__ import annotations

import yaml

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_group(repo_path: str = "", target_groups: int = 0, model_yaml: str = "") -> dict:
    """Group repository modules by the model's A1 containment partition."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    if model_yaml and model_yaml.strip():
        doc = yaml.safe_load(model_yaml)
        if doc is None:
            raise ValueError("empty model_yaml document")
    else:
        from opencode_arch.mcp.tools._openag_loader import load_doc
        doc = load_doc(repo_path)

    from openag.graph.model_graph import ModelGraph
    g = ModelGraph.from_doc(doc)

    from openag.kernel.grouping import group_modules
    return group_modules(g, target_groups=target_groups)
