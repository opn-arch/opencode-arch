"""arch_export — native openAG graph-file export MCP tool.

Behavioral replacement for the legacy AMS architect_export tool. Loads the
openAG model doc (inline model_yaml or the repo's merged model dir), builds the
in-memory ModelGraph, and writes a graph file (graphml/json-graph) into the
target directory via openag.graph.export_bundle.export_bundle. No legacy
architecture_model dependency.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_export(repo_path: str = "", output_dir: str = "", fmt: str = "graphml", model_yaml: str = "") -> dict:
    """Export the model as a graph file (graphml/json-graph) to a directory."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    if model_yaml and model_yaml.strip():
        doc = yaml.safe_load(model_yaml)
        if doc is None:
            raise ValueError("model_yaml is empty or not a mapping")
    else:
        from opencode_arch.mcp.tools._openag_loader import load_doc
        doc = load_doc(repo_path)

    from opencode_arch.mcp.tools._openag_loader import build_graph
    g = build_graph(doc)

    out = output_dir if output_dir else str(Path(repo_path) / ".architecture" / "export")

    from openag.graph.export_bundle import export_bundle
    return export_bundle(g, out, fmt=fmt)
