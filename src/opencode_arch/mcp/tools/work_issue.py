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
