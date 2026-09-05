"""architect_work_issue MCP tool — comment→issue→dev loop entrypoint."""

from __future__ import annotations

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
        }

    proposal_path = repo / final_job.result_ref
    proposal_data = _yaml.safe_load(proposal_path.read_text(encoding="utf-8"))
    proposal = proposal_from_dict(proposal_data)
    report = apply_proposal(repo, proposal, dry_run=dry_run)

    return {
        "ok": True,
        "work_order_id": work_order.id,
        "job_id": final_job.id,
        "package_revision_to": report.new_revision,
        "model_diff_digest": report.digest,
        "commit_sha": None,
        "dry_run": dry_run,
    }
