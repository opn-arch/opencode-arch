"""arch_job_get — fetch an AI Job by id (openAG-native).

openAG-native replacement for the AMS job-get tool. Reads the persisted Job via
``openag.ai.jobs.JobStore``. No AMS dependency.

Envelope
--------
Success: ``{"ok": True, "job": <job.to_dict()>}``

Errors
------
* ``INVALID_ARGUMENT`` — ``job_id`` empty/non-string; or ``repo_path`` invalid.
* ``NOT_FOUND`` — ``repo_path`` does not exist; OR job not found
  (``details.reason == "job_missing"``, ``details.job_id``).
* ``INTERNAL`` — unexpected exceptions.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_job_get(repo_path: str = "", job_id: str = "") -> dict:
    """Return the persisted Job identified by ``job_id``. See module docstring."""
    from opencode_arch.mcp.envelope import err, ok, resolve_repo
    from openag.ai.jobs import JobStore

    if not isinstance(job_id, str) or not job_id:
        return err("INVALID_ARGUMENT", "job_id must be a non-empty string")

    repo = resolve_repo(repo_path)

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


__all__ = ["arch_job_get"]
