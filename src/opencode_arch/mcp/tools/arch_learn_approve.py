"""arch_learn_approve — approval-gate release for a draft learning Job.

``arch_learn`` materializes a draft :class:`~openag.ai.work_order.WorkOrder`
plus a Job that STOPS at ``draft`` — the review gate. ``arch_learn_approve``
is the gate RELEASE: given that draft ``job_id`` it

1. transitions the Job ``draft → approved → queued``,
2. runs it through a proposer (injected in tests, otherwise resolved from
   ``.architecture/ai/proposer_config.yaml``) via
   :func:`openag.ai.worker.run_job`, driving the openAG Job state chain, and
3. applies the resulting ModelPatch to the current model doc and publishes a
   new generation — the same author→apply→publish path ``arch_work_issue``
   uses, minus the logs-db issue/comment ceremony.

Heavy ``openag.*`` imports are lazy (house convention).

Envelope
--------
Success: ``{"ok": True, "job_id", "job_state": "completed", "applied",
"package_revision_to", "model_diff_digest"}``.

A failed job (proposer raised, returned a non-ModelPatch, or the proposal
failed validation) returns ``ok: True`` with ``job_state="failed"``,
``applied=False``, and ``error`` echoed — the tool call itself succeeded.

Errors
------
* ``INVALID_ARGUMENT`` — empty ``job_id``; bad ``repo_path``.
* ``NOT_FOUND`` — ``repo_path`` missing; ``details.reason == "job_missing"``.
* ``PRECONDITION_FAILED`` — proposer-config faults (``details.reason`` in
  ``{"no_proposer_configured", "proposer_config_malformed",
  "proposer_plugin_not_loadable", "proposer_plugin_not_callable"}``).
* ``INTERNAL`` — unexpected faults.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_learn_approve(
    repo_path: str = "",
    *,
    job_id: str = "",
    dry_run: bool = False,
    proposer=None,
) -> dict:
    """Release a draft learning Job: author via proposer, then apply+publish."""
    import yaml

    from openag.ai.jobs import JobState, JobStore
    from openag.ai.worker import run_job
    from opencode_arch.mcp.envelope import err, ok, resolve_repo
    from opencode_arch.mcp.tools._devloop import (
        _ProposerConfigError,
        _apply_and_publish,
        _resolve_proposer_from_config,
    )

    if not job_id:
        return err("INVALID_ARGUMENT", "job_id must be a non-empty value")

    repo = resolve_repo(repo_path)

    # ---- Guard: unknown job -> NOT_FOUND before any transition ----------
    store = JobStore(root=repo)
    try:
        store.get(job_id)
    except KeyError:
        return err(
            "NOT_FOUND", f"job {job_id} not found", reason="job_missing"
        )

    # ---- Resolve proposer -----------------------------------------------
    if proposer is None:
        try:
            proposer = _resolve_proposer_from_config(repo)
        except _ProposerConfigError as exc:
            return err("PRECONDITION_FAILED", str(exc), reason=exc.reason)

    # ---- Release the gate: draft -> approved -> queued ------------------
    store.transition(job_id, JobState.approved, actor="arch_learn_approve")
    store.transition(job_id, JobState.queued, actor="arch_learn_approve")

    # ---- Run the job (author the proposal) ------------------------------
    final = run_job(str(repo), job_id, proposer=proposer)

    # ---- Failed job -> soft success envelope ----------------------------
    if final.state != JobState.completed:
        return ok(
            {
                "job_id": job_id,
                "job_state": final.state.value,
                "applied": False,
                "error": final.error or "unknown error",
            }
        )

    # ---- Apply + publish ------------------------------------------------
    proposal_path = repo / final.result_ref
    proposal_data = yaml.safe_load(proposal_path.read_text(encoding="utf-8"))
    apply_result, apply_error = _apply_and_publish(
        repo,
        proposal_data,
        dry_run=dry_run,
        reason=f"arch_learn_approve:{job_id}",
    )
    if apply_result is None:
        return ok(
            {
                "job_id": job_id,
                "job_state": "failed",
                "applied": False,
                "error": apply_error or "apply failed",
            }
        )

    return ok(
        {
            "job_id": job_id,
            "job_state": "completed",
            "applied": apply_result.applied,
            "package_revision_to": apply_result.new_revision,
            "model_diff_digest": apply_result.digest,
        }
    )


__all__ = ["arch_learn_approve"]
