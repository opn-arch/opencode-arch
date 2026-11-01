"""arch_work_issue — comment→issue→dev loop entrypoint (openAG-native).

openAG-native replacement for the AMS-era ``architect_work_issue`` tool.
Executes the full loop for a single logs-db issue:

1. Resolve the issue to a local comment stub (``openag.comments``).
2. Journal an ``issue.pull`` event (``openag.lifecycle.journal``).
3. (unless ``force``) short-circuit on an already-completed job for the
   same comment — idempotency.
4. Build a bounded :class:`~openag.ai.work_order.WorkOrder` from the stub.
5. Submit + run it through the configured (or injected) proposer via
   :func:`openag.ai.worker.run_job`, driving the openAG Job state chain.
6. Apply the resulting ModelPatch to the current model doc and publish a
   new generation (``openag.lifecycle.package.publish_generation``).
7. Post a progress comment, commit with trailers, and close the issue
   (OCA ceremony: ``logs_db`` client + ``lifecycle_exec.commit``).

No ``architecture_model`` dependency. The ``@arch_tool`` wrapper supplies
envelope normalization, proprioceptive spans, and mining telemetry.

Envelope
--------
Success: ``{"ok": True, "work_order_id", "job_id", "package_revision_to",
"model_diff_digest", "commit_sha", "issue_closed", "dry_run", "reused"}``.

A failed job (proposer raised, returned a non-ModelPatch, or the proposal
failed validation) returns ``ok: True`` with ``job_state="failed"``,
``applied=False``, and ``error`` echoed — the tool call itself succeeded.

Errors
------
* ``INVALID_ARGUMENT`` — empty/missing ``issue_id``; bad ``repo_path``.
* ``NOT_FOUND`` — ``repo_path`` missing; ``details.reason == "stub_missing"``.
* ``PRECONDITION_FAILED`` — ``details.reason`` in
  ``{"no_external_key", "no_proposer_configured",
  "proposer_config_malformed", "proposer_plugin_not_loadable",
  "proposer_plugin_not_callable"}``.
* ``INTERNAL`` — unexpected faults.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opencode_arch.mcp._arch_tool import arch_tool

DEFAULT_API_URL = "http://localhost:8000"
_PROPOSER_CONFIG_REL = ".architecture/ai/proposer_config.yaml"


class _ProposerConfigError(Exception):
    """Raised when the proposer config cannot be resolved; carries a reason."""

    def __init__(self, reason: str, message: str) -> None:
        self.reason = reason
        super().__init__(message)


@dataclass
class _ApplyResult:
    new_revision: str | None
    digest: str
    applied: bool


def _canonical_json(obj: Any) -> bytes:
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _resolve_proposer_from_config(repo: Path):
    """Load the proposer plugin from the repo's proposer config.

    Raises :class:`_ProposerConfigError` (with a ``reason``) on any fault.
    """
    import yaml

    cfg_path = repo / _PROPOSER_CONFIG_REL
    if not cfg_path.exists():
        raise _ProposerConfigError(
            "no_proposer_configured",
            "no proposer configured and none injected",
        )
    try:
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise _ProposerConfigError(
            "proposer_config_malformed", f"yaml parse error: {exc}"
        ) from exc
    if not isinstance(cfg, dict):
        raise _ProposerConfigError(
            "proposer_config_malformed", "top-level must be a mapping"
        )
    plugin = cfg.get("plugin")
    if not isinstance(plugin, str) or ":" not in plugin:
        raise _ProposerConfigError(
            "proposer_config_malformed",
            "'plugin' must be of the form 'module.path:function_name'",
        )
    module_path, _, func_name = plugin.partition(":")
    if not module_path or not func_name:
        raise _ProposerConfigError(
            "proposer_config_malformed",
            "'plugin' must be of the form 'module.path:function_name'",
        )
    try:
        module = importlib.import_module(module_path)
        fn = getattr(module, func_name)
    except (ImportError, AttributeError, ModuleNotFoundError) as exc:
        raise _ProposerConfigError(
            "proposer_plugin_not_loadable",
            f"proposer plugin not loadable: {exc}",
        ) from exc
    if not callable(fn):
        raise _ProposerConfigError(
            "proposer_plugin_not_callable",
            f"proposer plugin {plugin!r} is not callable",
        )
    return fn


def _existing_completed_job(repo: Path, *, comment_id: str):
    """Return a completed Job whose WorkOrder's ``comment_id`` matches, else None."""
    import yaml

    from openag.ai.jobs import JobState, JobStore
    from openag.ai.work_order import WorkOrder

    store = JobStore(root=repo)
    wo_dir = repo / ".architecture" / "ai" / "workorders"
    for job_id in store.list_ids():
        try:
            job = store.get(job_id)
        except KeyError:
            continue
        if job.state != JobState.completed:
            continue
        wo_path = wo_dir / f"{job.work_order_id}.yaml"
        if not wo_path.exists():
            continue
        try:
            wo = WorkOrder.from_dict(
                yaml.safe_load(wo_path.read_text(encoding="utf-8"))
            )
        except Exception:
            continue
        if wo.parameters.get("comment_id") == comment_id:
            return job
    return None


def _build_work_order(stub, *, issue_id, issue_url: str):
    from openag.ai.work_order import SliceRef, WorkOrder
    from opencode_arch.session import resolve_session_id

    intent = (
        stub.body[:200] + ("..." if len(stub.body) > 200 else "")
        + f"\n\nSource: {issue_url}"
    )
    return WorkOrder.build(
        intent=intent,
        slices=[SliceRef(slice_id=stub.slice_id, model_revision=stub.revision)],
        accepts=["model-patch"],
        max_tokens=200_000,
        max_wall_seconds=3600,
        requested_by=f"logs-db#{issue_id}",
        parameters={
            "issue_id": issue_id,
            "comment_id": stub.comment_id,
            "session_id": resolve_session_id(),
            "artifact_id": stub.artifact_id,
            "view_id": stub.view_id,
            "package_id": stub.package_id,
            "revision": stub.revision,
        },
    )


def _apply_and_publish(repo: Path, proposal_data: dict, *, dry_run: bool, reason: str):
    """Apply a ModelPatch to the current model doc; publish unless ``dry_run``.

    Returns ``(_ApplyResult, None)`` on success, or ``(None, error_str)`` when
    the proposal fails validation/apply.
    """
    from openag.llm.proposal import apply_proposal, proposal_from_dict
    from openag.model_io import load_model_dir

    doc = load_model_dir(str(repo / ".architecture" / "model"))
    prop = proposal_from_dict(proposal_data, task_class="", prompt_digest="")
    try:
        new_doc = apply_proposal(doc, prop)
    except ValueError as exc:
        return None, str(exc)

    digest = "sha256:" + hashlib.sha256(_canonical_json(new_doc)).hexdigest()
    if dry_run:
        return _ApplyResult(new_revision=None, digest=digest, applied=False), None

    from openag.lifecycle.package import publish_generation

    pub = publish_generation(str(repo), new_doc, reason=reason)
    return (
        _ApplyResult(new_revision=pub["gen_id"], digest=digest, applied=True),
        None,
    )


def _commit_and_close(
    repo: Path,
    client,
    *,
    issue: dict,
    stub,
    apply_result: _ApplyResult,
) -> str:
    """Post comment, commit with trailers, close issue, journal. Return SHA."""
    from openag.lifecycle.journal import ISSUE_CLOSE, Journal
    from opencode_arch.lifecycle_exec.commit import (
        build_trailers,
        commit_with_trailers,
    )
    from opencode_arch.session import resolve_session_id

    issue_id = issue["issue_id"]

    # Soft gate: informational progress comment (non-blocking).
    try:
        client.post_comment(
            issue_id,
            author="mcp",
            body=(
                f"Applied model patch: revision {apply_result.new_revision}, "
                f"digest {apply_result.digest}"
            ),
        )
    except Exception:
        pass

    trailers = build_trailers(
        issue_id=issue_id,
        comment_id=stub.comment_id,
        session_id=resolve_session_id(),
        revision_from=stub.revision,
        revision_to=apply_result.new_revision,
        model_diff_digest=apply_result.digest,
    )
    commit_sha = commit_with_trailers(
        repo,
        subject=f"chore(arch): apply proposal from logs-db#{issue_id}",
        body="",
        trailers=trailers,
    )

    client.close_issue(
        issue_id,
        commit_sha=commit_sha,
        model_diff_digest=apply_result.digest,
        note=f"Applied via arch_work_issue at {commit_sha[:8]}",
    )
    Journal(
        repo / ".architecture" / "lifecycle" / "journal.jsonl"
    ).record(
        ISSUE_CLOSE,
        {
            "actor": "arch_work_issue",
            "issue_id": issue_id,
            "comment_id": stub.comment_id,
            "commit_sha": commit_sha,
            "model_diff_digest": apply_result.digest,
        },
    )
    return commit_sha


@arch_tool
async def arch_work_issue(
    repo_path: str = "",
    *,
    issue_id: int | str = "",
    dry_run: bool = False,
    force: bool = False,
    proposer=None,
    client=None,
) -> dict:
    """Execute the comment→issue→dev loop for one logs-db issue. See module docstring."""
    import yaml

    from openag.ai.jobs import JobState, JobStore
    from openag.ai.worker import run_job
    from openag.comments.store import StubMissingError, load_stub
    from openag.lifecycle.journal import (
        ISSUE_PULL,
        WORKORDER_FROM_ISSUE,
        Journal,
    )
    from openag.lifecycle.atomic_store import write_atomic
    from opencode_arch.mcp.envelope import err, ok, resolve_repo

    if issue_id is None or (isinstance(issue_id, str) and not issue_id):
        return err("INVALID_ARGUMENT", "issue_id must be a non-empty value")

    repo = resolve_repo(repo_path)

    if client is None:
        from opencode_arch.logs_db.client import LogsDBClient

        client = LogsDBClient(os.environ.get("LOGS_DB_URL", DEFAULT_API_URL))

    # ---- 1. Resolve issue → comment stub --------------------------------
    issue = client.get_issue(issue_id)
    comment_id = issue.get("external_key")
    if not comment_id:
        return err(
            "PRECONDITION_FAILED",
            f"issue {issue_id} has no external_key",
            reason="no_external_key",
        )
    try:
        stub = load_stub(repo, comment_id)
    except StubMissingError:
        return err(
            "NOT_FOUND",
            f"comment stub missing for comment_id={comment_id}",
            reason="stub_missing",
            comment_id=comment_id,
        )

    journal = Journal(repo / ".architecture" / "lifecycle" / "journal.jsonl")
    journal.record(
        ISSUE_PULL,
        {
            "actor": "arch_work_issue",
            "issue_id": issue_id,
            "comment_id": comment_id,
            "package_revision": stub.revision,
        },
    )

    # ---- 2. Idempotency -------------------------------------------------
    if not force:
        prior = _existing_completed_job(repo, comment_id=comment_id)
        if prior is not None:
            return ok(
                {
                    "reused": True,
                    "work_order_id": prior.work_order_id,
                    "job_id": prior.id,
                    "commit_sha": None,
                    "issue_closed": False,
                    "dry_run": dry_run,
                }
            )

    # ---- 3. Resolve proposer --------------------------------------------
    if proposer is None:
        try:
            proposer = _resolve_proposer_from_config(repo)
        except _ProposerConfigError as exc:
            return err("PRECONDITION_FAILED", str(exc), reason=exc.reason)

    # ---- 4. Build + submit + run WorkOrder ------------------------------
    wo = _build_work_order(
        stub, issue_id=issue_id, issue_url=issue.get("url", "")
    )

    wo_dir = repo / ".architecture" / "ai" / "workorders"
    wo_dir.mkdir(parents=True, exist_ok=True)
    write_atomic(
        wo_dir / f"{wo.id}.yaml",
        yaml.safe_dump(wo.to_dict(), sort_keys=True).encode("utf-8"),
    )

    store = JobStore(root=repo)
    job = store.create(work_order_id=wo.id, actor="arch_work_issue")
    store.transition(job.id, JobState.approved, actor="arch_work_issue")
    store.transition(job.id, JobState.queued, actor="arch_work_issue")

    journal.record(
        WORKORDER_FROM_ISSUE,
        {
            "actor": "arch_work_issue",
            "issue_id": issue_id,
            "comment_id": comment_id,
            "work_order_id": wo.id,
            "job_id": job.id,
        },
    )

    try:
        final = run_job(str(repo), job.id, proposer=proposer)
    except Exception as exc:  # noqa: BLE001
        return err("INTERNAL", f"{type(exc).__name__}: {exc}")

    # ---- 5. Failed job → soft envelope ----------------------------------
    if final.state != JobState.completed:
        error_msg = final.error or "unknown error"
        try:
            client.post_comment(
                issue["issue_id"], author="mcp",
                body=f"Job {final.id} failed: {error_msg}",
            )
        except Exception:
            pass
        return ok(
            {
                "reused": False,
                "work_order_id": wo.id,
                "job_id": final.id,
                "job_state": final.state.value,
                "applied": False,
                "error": error_msg,
                "commit_sha": None,
                "issue_closed": False,
                "dry_run": dry_run,
            }
        )

    # ---- 6. Apply + publish ---------------------------------------------
    proposal_path = repo / final.result_ref
    proposal_data = yaml.safe_load(proposal_path.read_text(encoding="utf-8"))
    apply_result, apply_error = _apply_and_publish(
        repo,
        proposal_data,
        dry_run=dry_run,
        reason=f"arch_work_issue:logs-db#{issue_id}",
    )
    if apply_result is None:
        return ok(
            {
                "reused": False,
                "work_order_id": wo.id,
                "job_id": final.id,
                "job_state": "failed",
                "applied": False,
                "error": apply_error or "apply failed",
                "commit_sha": None,
                "issue_closed": False,
                "dry_run": dry_run,
            }
        )

    # ---- 7. Commit + close (skipped on dry_run) -------------------------
    env: dict[str, Any] = {
        "reused": False,
        "work_order_id": wo.id,
        "job_id": final.id,
        "package_revision_to": apply_result.new_revision,
        "model_diff_digest": apply_result.digest,
        "commit_sha": None,
        "issue_closed": False,
        "dry_run": dry_run,
    }
    if not dry_run:
        commit_sha = _commit_and_close(
            repo, client, issue=issue, stub=stub, apply_result=apply_result
        )
        env["commit_sha"] = commit_sha
        env["issue_closed"] = True
    return ok(env)


__all__ = ["arch_work_issue"]
