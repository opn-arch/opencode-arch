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
