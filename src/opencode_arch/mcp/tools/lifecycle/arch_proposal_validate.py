"""arch_proposal_validate — native openAG typed-proposal validation MCP tool.

Behavioral replacement for the legacy AMS architect_proposal_validate tool.
Parses a provider ModelPatch dict into a typed Proposal and runs every openAG
validation gate (schema, A1 strict partition, acyclic contains, file-coverage)
against the model doc via openag.lifecycle.proposals.validate_proposal_doc. The
model doc is either supplied inline as ``model_yaml`` or loaded from the repo's
openAG model dir. No legacy architecture_model dependency.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_proposal_validate(
    repo_path: str = "",
    proposal: dict | None = None,
    model_yaml: str = "",
    task_class: str = "",
    prompt_digest: str = "",
) -> dict:
    """Validate a typed proposal against an openAG model doc."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    if proposal is None or not isinstance(proposal, dict):
        raise ValueError("proposal is required")

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

    from openag.lifecycle.proposals import validate_proposal_doc

    return validate_proposal_doc(
        doc, proposal, task_class=task_class, prompt_digest=prompt_digest
    )
