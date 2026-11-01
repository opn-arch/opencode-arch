"""arch_decompose — native system-decomposition MCP tool over openAG.

Behavioral replacement for the legacy AMS architect_decompose tool. Loads the
openAG model graph (inline model_yaml or the repo's merged model dir) and
reports its System-level decomposition plus decomposition candidates via
openag.kernel.decompose_report.decompose_report. No legacy architecture_model
dependency.
"""
from __future__ import annotations

import yaml

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_decompose(repo_path: str = "", model_yaml: str = "") -> dict:
    """Report the model's System-level decomposition and split candidates."""
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

    from openag.kernel.decompose_report import decompose_report
    return decompose_report(g)
