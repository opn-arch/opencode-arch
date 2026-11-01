"""arch_ingest — native openAG SourceGraph-JSON ingestion MCP tool.

Behavioral replacement for the legacy AMS architect_ingest tool. Parses a
SourceGraph JSON string into a deterministic openAG model doc via
openag.graph.ingest.ingest_source_graph. No legacy architecture_model dependency.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_ingest(repo_path: str = "", source_graph_json: str = "") -> dict:
    """Ingest a SourceGraph JSON string into a deterministic openAG model doc."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    from openag.graph.ingest import ingest_source_graph
    result = ingest_source_graph(source_graph_json)

    return {
        "components": result["components"],
        "edges": result["edges"],
        "units": result["units"],
        "language": result["language"],
    }
