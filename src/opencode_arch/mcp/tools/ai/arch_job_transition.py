"""arch_job_transition — transition an AI Job to a new state (openAG-native).

openAG-native replacement for the AMS job-transition tool. Drives the Job state
machine via ``openag.ai.jobs.JobStore.transition``. No AMS dependency.

Envelope
--------
Success: ``{"ok": True, "job": <job.to_dict()>}``

Errors
------
* ``INVALID_ARGUMENT`` — ``job_id`` empty/non-str; unknown ``new_state``
  (``details.new_state``, ``details.valid_states``); non-string optional arg; or a
  missing accompanying field for a terminal transition (``details.reason == str(exc)``).
* ``NOT_FOUND`` — ``repo_path`` does not exist; OR job not found
  (``details.reason == "job_missing"``, ``details.job_id``).
* ``PRECONDITION_FAILED`` — illegal state transition (``details.from_state``,
  ``details.to_state``, ``details.allowed`` sorted ``list[str]``).
* ``INTERNAL`` — unexpected exceptions.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_job_transition(
    repo_path: str = "",
    job_id: str = "",
    new_state: str = "",
    reason: str | None = None,
    actor: str | None = None,
    result_ref: str | None = None,
    error: str | None = None,
) -> dict:
    """Transition ``job_id`` to ``new_state``. See module docstring."""
    from opencode_arch.mcp.envelope import err, ok, resolve_repo
    from openag.ai.jobs import InvalidTransitionError, JobState, JobStore

    if not isinstance(job_id, str) or not job_id:
        return err("INVALID_ARGUMENT", "job_id must be a non-empty string")

    valid_states = sorted(s.value for s in JobState)
    if not isinstance(new_state, str) or not new_state:
        return err(
            "INVALID_ARGUMENT",
            "new_state must be a non-empty string",
            new_state=new_state,
            valid_states=valid_states,
        )
    try:
        target_state = JobState(new_state)
    except ValueError:
        return err(
            "INVALID_ARGUMENT",
            f"unknown new_state {new_state!r}",
            new_state=new_state,
            valid_states=valid_states,
        )

    for name, value in (
        ("reason", reason),
        ("actor", actor),
        ("result_ref", result_ref),
        ("error", error),
    ):
        if value is not None and not isinstance(value, str):
            return err("INVALID_ARGUMENT", f"{name} must be a string or None")

    repo = resolve_repo(repo_path)

    store = JobStore(root=repo)
    try:
        job = store.transition(
            job_id,
            target_state,
            reason=reason,
            actor=actor or "system",
            result_ref=result_ref,
            error=error,
        )
    except KeyError:
        return err(
            "NOT_FOUND",
            f"job {job_id!r} not found",
            reason="job_missing",
            job_id=job_id,
        )
    except InvalidTransitionError as exc:
        return err(
            "PRECONDITION_FAILED",
            str(exc),
            from_state=exc.from_state.value,
            to_state=exc.to_state.value,
            allowed=sorted(s.value for s in exc.allowed),
        )
    except ValueError as exc:
        return err("INVALID_ARGUMENT", str(exc), reason=str(exc))

    return ok({"job": job.to_dict()})


__all__ = ["arch_job_transition"]
