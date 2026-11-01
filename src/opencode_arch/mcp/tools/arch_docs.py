"""arch_docs — native openAG-shaped SE documentation MCP tool.

Behavioral replacement for the legacy AMS architect_docs tool. Loads the
openAG model doc (inline model_yaml or the repo's merged model dir) and
generates the openAG-shaped markdown doc set via
openag.viewer.docs.generate_docs. No legacy architecture_model dependency.
"""
from __future__ import annotations

import yaml

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_docs(repo_path: str = "", formats: str = "all", model_yaml: str = "") -> dict:
    """Generate openAG-shaped SE documentation from the model."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    if model_yaml and model_yaml.strip():
        doc = yaml.safe_load(model_yaml)
        if doc is None:
            raise ValueError("model_yaml is empty or not a mapping")
    else:
        from opencode_arch.mcp.tools._openag_loader import load_doc
        doc = load_doc(repo_path)

    stripped = formats.strip()
    if stripped == "all" or not stripped:
        fmts = ("all",)
    else:
        fmts = tuple(f.strip() for f in formats.split(",") if f.strip())

    from openag.viewer.docs import generate_docs
    docs = generate_docs(doc, formats=fmts)
    return {"docs": docs, "count": len(docs)}
