"""arch_feedback — native openAG user-feedback MCP tool.

Behavioral replacement for the legacy AMS architect_feedback tool. Appends a
user-feedback record to the repo's feedback JSONL ledger via
openag.mining.feedback.record_feedback. No legacy architecture_model dependency.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_feedback(
    repo_path: str = "",
    feedback_type: str = "",
    content: str = "",
    context: dict | None = None,
    rating: int | None = None,
    correction: dict | None = None,
) -> dict:
    """Record user feedback for model improvement into the repo ledger."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    from openag.mining.feedback import record_feedback
    return record_feedback(
        repo_path,
        feedback_type,
        content,
        context=context,
        rating=rating,
        correction=correction,
    )
