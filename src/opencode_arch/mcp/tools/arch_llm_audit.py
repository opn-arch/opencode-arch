"""arch_llm_audit — native openAG decomposition second-opinion MCP tool.

Behavioral replacement for the legacy AMS architect_llm_audit tool. Runs a
deterministic structural second-opinion audit over the model's decomposition via
openag.kernel.llm_audit.audit_decomposition. No legacy architecture_model dependency.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_llm_audit(repo_path: str = "", model_yaml: str = "") -> dict:
    """Run a deterministic decomposition second-opinion audit over the model."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    import yaml
    if model_yaml:
        doc = yaml.safe_load(model_yaml)
        if doc is None:
            raise ValueError("model_yaml parsed to None")
    else:
        from opencode_arch.mcp.tools._openag_loader import load_doc
        doc = load_doc(repo_path)

    from openag.graph.model_graph import ModelGraph
    g = ModelGraph.from_doc(doc)

    from openag.kernel.llm_audit import audit_decomposition
    return audit_decomposition(g)
