"""AI job worker executor (T15).

Provides two pure-Python entry points for advancing an AI ``Job`` from
``queued`` through ``running`` and ``validating`` to a terminal state
(``completed`` or ``failed``). No MCP registration lives here — the
:mod:`opencode_arch.mcp.tools.ai` layer (T16) is responsible for
wrapping these callables in tool envelopes.

Contract
--------
* :func:`dequeue_next` returns the queued job with the earliest
  ``created_at`` (or ``None`` if none). ``created_at`` is an ISO-8601
  UTC string; lexicographic comparison is monotonic for that format.
* :func:`run_job` executes exactly one job. It never lets an exception
  escape once the job is picked up (steps 4+), instead transitioning to
  ``failed`` with a descriptive error. Contract violations detected
  *before* the ``queued → running`` transition (missing job, missing
  work-order YAML, wrong state) propagate to the caller.

Persistence
-----------
Proposals are written atomically to
``<repo>/.architecture/ai/proposals/<job_id>.yaml`` via
:func:`architecture_model.lifecycle.atomic_store.write_atomic` using
``yaml.safe_dump`` with ``sort_keys=True, default_flow_style=False``.
The persisted ``result_ref`` on the completed job is the POSIX-relative
path from the repo root (forward slashes).
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import yaml

from architecture_model.ai.jobs import Job, JobState, JobStore
from architecture_model.ai.proposals import (
    ArtifactCandidate,
    DecompositionProposal,
    ImpactAssessment,
    ModelPatch,
    SliceProposal,
    ViewCurationProposal,
)
from architecture_model.ai.validators import validate
from architecture_model.ai.work_order import WorkOrder
from architecture_model.lifecycle.atomic_store import write_atomic

PROPOSAL_TYPES: tuple[type, ...] = (
    ModelPatch,
    DecompositionProposal,
    SliceProposal,
    ViewCurationProposal,
    ArtifactCandidate,
    ImpactAssessment,
)


def dequeue_next(repo_path: str | Path) -> Job | None:
    """Return the queued job with the earliest ``created_at`` or ``None``.

    Raises :class:`ValueError` if ``repo_path`` does not exist.
    """
    repo = Path(repo_path)
    if not repo.exists():
        raise ValueError(f"repo_path does not exist: {repo}")
    store = JobStore(root=repo)
    queued: list[Job] = []
    for jid in store.list_ids():
        try:
            job = store.get(jid)
        except KeyError:
            continue
        if job.state == JobState.queued:
            queued.append(job)
    if not queued:
        return None
    queued.sort(key=lambda j: j.created_at)
    return queued[0]


def _load_work_order(repo: Path, work_order_id: str) -> WorkOrder:
    wo_path = repo / ".architecture" / "ai" / "workorders" / f"{work_order_id}.yaml"
    if not wo_path.exists():
        raise FileNotFoundError(
            f"work order YAML not found: {wo_path}"
        )
    data = yaml.safe_load(wo_path.read_text(encoding="utf-8"))
    return WorkOrder.from_dict(data)


def _fail(
    store: JobStore, job_id: str, from_state: JobState, error: str
) -> Job:
    """Transition to failed from the current state."""
    # Determine the correct target: if in validating, allowed → failed;
    # if in running, allowed → failed. Both routes are legal.
    return store.transition(
        job_id,
        JobState.failed,
        actor="worker",
        error=error,
    )


def run_job(
    repo_path: str | Path,
    job_id: str,
    *,
    proposer: Callable[[WorkOrder], object],
    input_slices: dict[str, dict] | None = None,
) -> Job:
    """Execute one queued job end-to-end.

    Returns the final :class:`Job` (post terminal transition).
    Raises :class:`KeyError` if ``job_id`` is unknown,
    :class:`ValueError` if the job is not in ``queued``, and
    :class:`FileNotFoundError` if the work-order YAML is missing.
    All other failures are captured on the job as ``state=failed``.
    """
    repo = Path(repo_path)
    store = JobStore(root=repo)

    # Step 1: load job (KeyError propagates).
    job = store.get(job_id)

    # Step 2: enforce queued precondition.
    if job.state != JobState.queued:
        raise ValueError(
            f"job {job_id!r} is not queued (state={job.state.value})"
        )

    # Step 3: load WorkOrder (FileNotFoundError propagates).
    work_order = _load_work_order(repo, job.work_order_id)

    # Step 4: queued → running.
    job = store.transition(
        job_id, JobState.running, actor="worker", reason="dequeued"
    )

    # Step 5: invoke proposer.
    try:
        result = proposer(work_order)
    except Exception as exc:  # noqa: BLE001 — worker contract
        return _fail(
            store, job_id, JobState.running, f"proposer error: {exc}"
        )

    # Step 6: type check the proposal.
    if not isinstance(result, PROPOSAL_TYPES):
        return _fail(
            store,
            job_id,
            JobState.running,
            "proposer returned non-Proposal object",
        )

    proposal = result
    slices = input_slices if input_slices is not None else {}

    # Steps 7-11 are guarded against unexpected exceptions.
    try:
        # Step 7: persist proposal atomically.
        proposals_dir = repo / ".architecture" / "ai" / "proposals"
        proposals_dir.mkdir(parents=True, exist_ok=True)
        proposal_path = proposals_dir / f"{job_id}.yaml"
        text = yaml.safe_dump(
            proposal.to_dict(),
            sort_keys=True,
            default_flow_style=False,
        )
        write_atomic(proposal_path, text.encode("utf-8"))

        # Step 8: running → validating.
        job = store.transition(
            job_id, JobState.validating, actor="worker"
        )

        # Step 9: validate.
        report = validate(proposal, work_order=work_order, input_slices=slices)
    except Exception as exc:  # noqa: BLE001
        # We may already be in ``validating``; either state can transition
        # to ``failed``.
        current = store.get(job_id)
        return _fail(
            store, job_id, current.state, f"executor error: {exc}"
        )

    # Steps 10/11: terminal transition.
    if report.passed:
        rel = proposal_path.relative_to(repo).as_posix()
        return store.transition(
            job_id,
            JobState.completed,
            actor="worker",
            result_ref=rel,
        )

    errors = [f for f in report.findings if f.severity == "error"]
    first = errors[0].message if errors else "unknown"
    return store.transition(
        job_id,
        JobState.failed,
        actor="worker",
        error=f"validation failed: {len(errors)} error(s); first: {first}",
    )


__all__ = ["dequeue_next", "run_job", "PROPOSAL_TYPES"]
