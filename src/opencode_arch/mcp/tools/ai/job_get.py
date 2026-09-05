"""MCP tool: fetch an AI Job by id.

Envelope
--------
Success: ``{"ok": True, "job": <job.to_dict()>}``

Errors
------
* ``INVALID_ARGUMENT`` — ``job_id`` is empty or not a string.
* ``NOT_FOUND`` — ``repo_path`` missing (``details.reason ==
  "repo_missing"``) OR job not found (``details.reason ==
  "job_missing"``).
* ``INTERNAL`` — unexpected exceptions.
"""
from __future__ import annotations

from pathlib import Path

from opencode_arch.mcp.envelope import err, ok, tool_result


@tool_result
async def architect_job_get_tool(repo_path: str, job_id: str) -> dict:
    """Return the persisted Job identified by ``job_id``."""
    if not isinstance(job_id, str) or not job_id:
        return err("INVALID_ARGUMENT", "job_id must be a non-empty string")

    if not isinstance(repo_path, str) or not repo_path:
        return err(
            "NOT_FOUND",
            "repo_path does not exist",
            reason="repo_missing",
        )
    repo = Path(repo_path).expanduser().resolve()
    if not repo.exists() or not repo.is_dir():
        return err(
            "NOT_FOUND",
            f"repo_path does not exist: {repo}",
            reason="repo_missing",
        )

    from architecture_model.ai.jobs import JobStore

    store = JobStore(root=repo)
    try:
        job = store.get(job_id)
    except KeyError:
        return err(
            "NOT_FOUND",
            f"job {job_id!r} not found",
            reason="job_missing",
            job_id=job_id,
        )

    return ok({"job": job.to_dict()})


__all__ = ["architect_job_get_tool"]
