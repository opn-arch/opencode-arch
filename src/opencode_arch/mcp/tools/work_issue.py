"""architect_work_issue MCP tool — comment→issue→dev loop entrypoint."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from architecture_model.comments.models import CommentStub
from architecture_model.comments.store import load_stub, StubMissingError
from architecture_model.lifecycle.journal import Journal, ISSUE_PULL
from opencode_arch.logs_db.client import LogsDBClient


class WorkIssueError(RuntimeError):
    pass


@dataclass
class _WorkContext:
    repo_path: Path
    issue: dict
    stub: CommentStub


def _load_and_resolve(repo_path: Path, client: LogsDBClient, issue_id: int | str) -> _WorkContext:
    issue = client.get_issue(issue_id)
    comment_id = issue.get("external_key")
    if not comment_id:
        raise WorkIssueError(f"issue {issue_id} has no external_key")
    try:
        stub = load_stub(repo_path, comment_id)
    except StubMissingError as e:
        raise WorkIssueError(f"stub missing for comment_id={comment_id}: {e}") from e
    journal = Journal(repo_path / ".architecture" / "lifecycle" / "journal.jsonl")
    journal.record(ISSUE_PULL, {
        "issue_id": issue_id, "comment_id": comment_id,
        "package_revision": stub.revision,
        "actor": "architect_work_issue",
    })
    return _WorkContext(repo_path=repo_path, issue=issue, stub=stub)


def _soft_gate(ctx: _WorkContext, client: LogsDBClient, apply_report) -> dict | None:
    """Post an informational progress comment after apply. Non-blocking.

    TODO: integrate architect_check / architect_gate to run structural checks
    on the newly published model. For now, just post revision + digest so a
    human reviewer can trace the change.
    """
    if apply_report.new_revision is None:
        return None
    body = (
        f"Applied model patch: revision {apply_report.new_revision}, "
        f"digest {apply_report.digest}"
    )
    posted = False
    try:
        client.post_comment(ctx.issue["issue_id"], author="mcp", body=body)
        posted = True
    except Exception:
        pass
    return {"posted": posted, "comment": body}


def _rebuild_affected(ctx: _WorkContext, apply_report) -> list:
    """Rebuild artifacts affected by the applied patch.

    TODO(A4.2 follow-up): full ArtifactSpec-driven rebuild requires fixtures
    to be authored. Stub returns []; the loop continues so Plan A can close.
    """
    if apply_report.new_revision is None:
        return []
    return []


def _commit_step(ctx: _WorkContext, apply_report, *, provider: str | None = None) -> str:
    from opencode_arch.lifecycle_exec.commit import build_trailers, commit_with_trailers

    issue_id = ctx.issue["issue_id"]
    trailers = build_trailers(
        issue_id=issue_id,
        comment_id=ctx.stub.comment_id,
        session_id=resolve_session_id(),
        revision_from=ctx.stub.revision,
        revision_to=apply_report.new_revision,
        model_diff_digest=apply_report.digest,
        provider=provider,
    )
    return commit_with_trailers(
        ctx.repo_path,
        subject=f"chore(arch): apply proposal from logs-db#{issue_id}",
        body="",
        trailers=trailers,
    )


def _close_issue(
    ctx: _WorkContext, client: LogsDBClient, *, commit_sha: str, model_diff_digest: str,
) -> dict:
    from architecture_model.lifecycle.journal import ISSUE_CLOSE

    issue_id = ctx.issue["issue_id"]
    resp = client.close_issue(
        issue_id,
        commit_sha=commit_sha,
        model_diff_digest=model_diff_digest,
        note=f"Applied via architect_work_issue at {commit_sha[:8]}",
    )
    journal = Journal(ctx.repo_path / ".architecture" / "lifecycle" / "journal.jsonl")
    journal.record(ISSUE_CLOSE, {
        "actor": "architect_work_issue",
        "issue_id": issue_id,
        "comment_id": ctx.stub.comment_id,
        "commit_sha": commit_sha,
        "model_diff_digest": model_diff_digest,
    })
    return resp


from architecture_model.ai.work_order import WorkOrder, SliceRef
from opencode_arch.session import resolve_session_id


def _workorder_from_stub(*, stub: CommentStub, issue_id: int | str, issue_url: str) -> WorkOrder:
    intent = (stub.body[:200] + ("..." if len(stub.body) > 200 else "")) \
        + f"\n\nSource: {issue_url}"
    return WorkOrder.build(
        intent=intent,
        slices=[SliceRef(slice_id=stub.slice_id, model_revision=stub.revision)],
        accepts=["model-patch"],
        max_tokens=200_000,
        max_wall_seconds=3600,
        requested_by=f"logs-db#{issue_id}",
        parameters={
            "issue_id": issue_id, "comment_id": stub.comment_id,
            "session_id": resolve_session_id(),
            "artifact_id": stub.artifact_id, "view_id": stub.view_id,
            "package_id": stub.package_id, "revision": stub.revision,
        },
    )


def _existing_completed_job(repo_path: Path, *, comment_id: str):
    """Return a completed Job whose WorkOrder has parameters.comment_id == comment_id, else None."""
    from architecture_model.ai.jobs import JobStore, JobState
    from architecture_model.ai.work_order import WorkOrder
    import yaml as _yaml

    js = JobStore(repo_path)
    wo_dir = repo_path / ".architecture" / "ai" / "workorders"
    for job_id in js.list_ids():
        try:
            job = js.get(job_id)
        except KeyError:
            continue
        if job.state != JobState.completed:
            continue
        wo_path = wo_dir / f"{job.work_order_id}.yaml"
        if not wo_path.exists():
            continue
        try:
            wo = WorkOrder.from_dict(_yaml.safe_load(wo_path.read_text(encoding="utf-8")))
        except Exception:
            continue
        if wo.parameters.get("comment_id") == comment_id:
            return job
    return None


def _submit_run_validate_apply(
    ctx: _WorkContext,
    work_order,
    *,
    client: LogsDBClient,
    proposer,
    dry_run: bool = False,
) -> dict:
    """Steps 6-9 of the work-issue flow: submit WorkOrder, run proposer, validate, apply."""
    from architecture_model.ai.jobs import JobStore, JobState
    from architecture_model.ai.proposals import proposal_from_dict
    from architecture_model.lifecycle.atomic_store import write_atomic
    from architecture_model.lifecycle.journal import WORKORDER_FROM_ISSUE
    from opencode_arch.lifecycle_exec.worker import run_job
    from opencode_arch.lifecycle_exec.apply import apply_proposal
    import yaml as _yaml

    repo = ctx.repo_path

    wo_dir = repo / ".architecture" / "ai" / "workorders"
    wo_dir.mkdir(parents=True, exist_ok=True)
    write_atomic(
        wo_dir / f"{work_order.id}.yaml",
        _yaml.safe_dump(work_order.to_dict(), sort_keys=True).encode("utf-8"),
    )

    js = JobStore(repo)
    job = js.create(work_order_id=work_order.id, actor="architect_work_issue")
    js.transition(job.id, JobState.approved, actor="architect_work_issue")
    js.transition(job.id, JobState.queued, actor="architect_work_issue")

    journal = Journal(repo / ".architecture" / "lifecycle" / "journal.jsonl")
    journal.record(WORKORDER_FROM_ISSUE, {
        "actor": "architect_work_issue",
        "issue_id": ctx.issue.get("issue_id"),
        "comment_id": ctx.stub.comment_id,
        "work_order_id": work_order.id,
        "job_id": job.id,
    })

    final_job = run_job(repo, job.id, proposer=proposer)

    if final_job.state != JobState.completed:
        error_msg = final_job.error or "unknown error"
        try:
            client.post_comment(
                ctx.issue["issue_id"], author="mcp",
                body=f"Job {final_job.id} failed: {error_msg}",
            )
        except Exception:
            pass
        return {
            "ok": False,
            "error": "proposal_invalid",
            "job_id": final_job.id,
            "work_order_id": work_order.id,
            "message": error_msg,
        }, None

    proposal_path = repo / final_job.result_ref
    proposal_data = _yaml.safe_load(proposal_path.read_text(encoding="utf-8"))
    proposal = proposal_from_dict(proposal_data)
    report = apply_proposal(repo, proposal, dry_run=dry_run)

    env = {
        "ok": True,
        "work_order_id": work_order.id,
        "job_id": final_job.id,
        "package_revision_to": report.new_revision,
        "model_diff_digest": report.digest,
        "commit_sha": None,
        "dry_run": dry_run,
    }
    return env, report


def _resolve_logs_db_url(repo_path: Path) -> str:
    from opencode_arch.mcp.tools.sync import DEFAULT_API_URL
    return os.environ.get("LOGS_DB_URL", DEFAULT_API_URL)


def _resolve_proposer(repo_path: Path):
    """Load proposer plugin from .architecture/ai/proposer_config.yaml."""
    import importlib
    import yaml as _yaml
    cfg_path = repo_path / ".architecture" / "ai" / "proposer_config.yaml"
    if not cfg_path.exists():
        raise WorkIssueError("no proposer configured (.architecture/ai/proposer_config.yaml missing)")
    cfg = _yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    plugin = cfg.get("plugin")
    if not plugin or ":" not in plugin:
        raise WorkIssueError("proposer_config.yaml missing 'plugin: module.path:function_name'")
    mod_path, fn_name = plugin.split(":", 1)
    module = importlib.import_module(mod_path)
    fn = getattr(module, fn_name, None)
    if not callable(fn):
        raise WorkIssueError(f"proposer plugin {plugin!r} is not callable")
    return fn


def architect_work_issue(
    repo_path: str,
    *,
    issue_id: int | str,
    dry_run: bool = False,
    force: bool = False,
    proposer=None,
) -> dict:
    """Execute the comment→issue→dev loop for a single logs-db issue.

    Steps 1-9 (Phase A3). Steps 10-13 (rebuild/commit/close) land in Phase A4.
    """
    repo = Path(repo_path).resolve()
    client = LogsDBClient(_resolve_logs_db_url(repo))

    ctx = _load_and_resolve(repo, client, issue_id)

    if not force:
        prior = _existing_completed_job(repo, comment_id=ctx.stub.comment_id)
        if prior is not None:
            return {
                "ok": True,
                "reused": True,
                "work_order_id": prior.work_order_id,
                "job_id": prior.id,
                "commit_sha": None,
            }

    wo = _workorder_from_stub(
        stub=ctx.stub,
        issue_id=issue_id,
        issue_url=ctx.issue.get("url", ""),
    )

    if proposer is None:
        proposer = _resolve_proposer(repo)

    env, apply_report = _submit_run_validate_apply(
        ctx, wo, client=client, proposer=proposer, dry_run=dry_run,
    )
    return _finalize(ctx, client, env, apply_report)


def _finalize(ctx: _WorkContext, client: LogsDBClient, env: dict, apply_report) -> dict:
    if not env.get("ok") or apply_report is None or apply_report.new_revision is None:
        return env
    _soft_gate(ctx, client, apply_report)
    _rebuild_affected(ctx, apply_report)
    commit_sha = _commit_step(ctx, apply_report)
    _close_issue(
        ctx, client,
        commit_sha=commit_sha,
        model_diff_digest=apply_report.digest,
    )
    env["commit_sha"] = commit_sha
    env["issue_closed"] = True
    return env
