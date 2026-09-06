"""MCP tool: apply an AI Proposal to the repo's lifecycle store (T19).

Envelope
--------
Success: ``{"ok": True, "report": <dataclasses.asdict(ApplyReport)>}``.

Errors
------
* ``INVALID_ARGUMENT`` — ``proposal`` not a dict; ``work_order_id`` empty
  / non-string; ``dry_run`` not a bool.
* ``NOT_FOUND`` — repo missing, or Phase 1 raised
  :class:`PackageNotFoundError` (``details.reason`` = str(exc)).
* ``SCHEMA_VIOLATION`` — proposal parse failed or Phase 1 raised
  :class:`InvalidProposalError` (``details.reason`` = str(exc)).
* ``PRECONDITION_FAILED`` — one of:
  - ``details.reason == "workorder_missing"``
  - ``details.reason == "job_missing"``
  - ``details.reason == "job_not_completed"`` (``details.state``)
  - ``details.reason == "proposal_mismatch"`` (identity check failed)
  - Phase 1 raised :class:`DriftError` (``details.expected``,
    ``details.actual``).
* ``INTERNAL`` — any other unexpected exception (no stack leaked).

Journal
-------
On non-dry-run success, a single ``ai.proposal.apply`` event is recorded
in addition to whatever per-kind events :mod:`opencode_arch.lifecycle_exec.apply`
already wrote. Payload::

    {proposal_id, work_order_id, job_id, dry_run, ok, new_revision,
     digest, kind}

The event is NOT recorded on dry-run or on any error path.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

# Module-level import so tests can monkeypatch this seam.
from opencode_arch.lifecycle_exec.apply import apply_proposal
from opencode_arch.mcp.envelope import err, ok, resolve_repo, tool_result
from architecture_model.sil.decorators import instrumented


def _extract_identity(proposal: dict) -> tuple[str | None, str | None]:
    """Return ``(work_order_id, prompt_digest)`` from a proposal dict."""
    prov = proposal.get("provenance") if isinstance(proposal, dict) else None
    if not isinstance(prov, dict):
        return None, None
    return prov.get("work_order_id"), prov.get("prompt_digest")


def _json_safe(value: Any) -> Any:
    """Recursively coerce Path → str; leave everything else."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    return value


@instrumented("mcp_tool:architect_proposal_apply")
@tool_result
async def architect_proposal_apply_tool(
    repo_path: str,
    proposal: dict,
    work_order_id: str,
    dry_run: bool = True,
) -> dict:
    """Apply a persisted, completed proposal to the lifecycle store."""
    if not isinstance(proposal, dict):
        return err("INVALID_ARGUMENT", "proposal must be a dict")
    if not isinstance(work_order_id, str) or not work_order_id:
        return err(
            "INVALID_ARGUMENT", "work_order_id must be a non-empty string"
        )
    if not isinstance(dry_run, bool):
        return err("INVALID_ARGUMENT", "dry_run must be a bool")

    repo = resolve_repo(repo_path)

    # ---- Precondition: WorkOrder file exists ---------------------------
    wo_path = (
        repo / ".architecture" / "ai" / "workorders" / f"{work_order_id}.yaml"
    )
    if not wo_path.exists():
        return err(
            "PRECONDITION_FAILED",
            f"work order {work_order_id!r} not found",
            reason="workorder_missing",
            work_order_id=work_order_id,
        )

    # ---- Precondition: locate the tracking Job -------------------------
    from architecture_model.ai.jobs import JobState, JobStore

    store = JobStore(root=repo)
    matched_job = None
    matched_non_completed = None
    for jid in store.list_ids():
        try:
            j = store.get(jid)
        except KeyError:
            continue
        if j.work_order_id != work_order_id:
            continue
        if j.state == JobState.completed:
            matched_job = j
            break
        matched_non_completed = j

    if matched_job is None:
        if matched_non_completed is not None:
            return err(
                "PRECONDITION_FAILED",
                f"job for work_order {work_order_id!r} is not completed",
                reason="job_not_completed",
                state=matched_non_completed.state.value,
                job_id=matched_non_completed.id,
            )
        return err(
            "PRECONDITION_FAILED",
            f"no job found for work_order {work_order_id!r}",
            reason="job_missing",
            work_order_id=work_order_id,
        )

    # ---- Precondition: proposal identity matches persisted result ------
    if not matched_job.result_ref:
        return err(
            "PRECONDITION_FAILED",
            "completed job has no result_ref",
            reason="proposal_mismatch",
            job_id=matched_job.id,
        )
    result_path = repo / matched_job.result_ref
    if not result_path.exists():
        return err(
            "PRECONDITION_FAILED",
            f"persisted proposal not found at {matched_job.result_ref}",
            reason="proposal_mismatch",
            job_id=matched_job.id,
        )
    try:
        import yaml

        persisted = yaml.safe_load(result_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return err(
            "PRECONDITION_FAILED",
            f"persisted proposal unreadable: {exc}",
            reason="proposal_mismatch",
            job_id=matched_job.id,
        )
    caller_wo, caller_digest = _extract_identity(proposal)
    persisted_wo, persisted_digest = _extract_identity(persisted or {})
    if (
        caller_wo != persisted_wo
        or caller_digest != persisted_digest
        or not caller_digest
    ):
        return err(
            "PRECONDITION_FAILED",
            "proposal identity does not match persisted proposal",
            reason="proposal_mismatch",
            job_id=matched_job.id,
        )

    # ---- Parse proposal ------------------------------------------------
    from architecture_model.ai import proposals as _prop_mod

    try:
        parsed = _prop_mod.proposal_from_dict(proposal)
    except (KeyError, ValueError, TypeError) as exc:
        return err(
            "SCHEMA_VIOLATION",
            f"proposal parse failed: {exc}",
            reason=str(exc),
        )

    # ---- Delegate ------------------------------------------------------
    from opencode_arch.lifecycle_exec.apply import (
        DriftError,
        InvalidProposalError,
        PackageNotFoundError,
    )

    try:
        # Use module-level lookup so tests can monkeypatch this seam.
        report = globals()["apply_proposal"](repo, parsed, dry_run=dry_run)
    except DriftError as exc:
        return err(
            "PRECONDITION_FAILED",
            str(exc),
            reason="drift",
            expected=exc.expected,
            actual=exc.actual,
        )
    except InvalidProposalError as exc:
        return err("SCHEMA_VIOLATION", str(exc), reason=str(exc))
    except PackageNotFoundError as exc:
        return err("NOT_FOUND", str(exc), reason=str(exc))
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as exc:  # noqa: BLE001
        # Single-line message; no traceback.
        msg = f"{type(exc).__name__}: {exc}".splitlines()[0]
        return err("INTERNAL", msg)

    report_dict = _json_safe(dataclasses.asdict(report))

    # ---- Journal (non-dry-run only) ------------------------------------
    if not dry_run:
        try:
            from architecture_model.lifecycle.journal import Journal

            journal_path = (
                repo / ".architecture" / "lifecycle" / "journal.jsonl"
            )
            Journal(journal_path).record(
                event="ai.proposal.apply",
                payload={
                    "proposal_id": caller_wo,
                    "work_order_id": work_order_id,
                    "job_id": matched_job.id,
                    "dry_run": dry_run,
                    "ok": True,
                    "new_revision": report.new_revision,
                    "digest": report.digest,
                    "kind": proposal.get("kind"),
                },
            )
        except Exception as exc:  # noqa: BLE001
            msg = f"{type(exc).__name__}: {exc}".splitlines()[0]
            return err("INTERNAL", f"journal record failed: {msg}")

    return ok({"report": report_dict})


__all__ = ["architect_proposal_apply_tool"]
