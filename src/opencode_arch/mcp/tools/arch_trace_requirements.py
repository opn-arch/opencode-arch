"""arch_trace_requirements — native openAG requirement-tracing MCP tool.

Behavioral replacement for the legacy AMS architect_trace_requirements tool.
Traces requirement texts to model entities by deterministic token overlap via
openag.compliance.trace.trace_requirements. Composes with the requirements
ledger written by arch_require. No legacy architecture_model dependency.
"""
from __future__ import annotations

from pathlib import Path

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_trace_requirements(
    repo_path: str = "", model_yaml: str = "", requirements_yaml: str = ""
) -> dict:
    """Trace requirements (from arg or the repo ledger) to model entities."""
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

    # Requirements: explicit arg wins; else read the repo ledger (may be absent).
    if requirements_yaml:
        parsed = yaml.safe_load(requirements_yaml)
    else:
        ledger = Path(repo_path) / ".architecture" / "requirements.yaml"
        parsed = yaml.safe_load(ledger.read_text()) if ledger.exists() else None
    if isinstance(parsed, dict):
        requirements = parsed.get("requirements") or []
    elif isinstance(parsed, list):
        requirements = parsed
    else:
        requirements = []

    from openag.compliance.trace import trace_requirements
    return trace_requirements(doc, requirements)
