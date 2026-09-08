"""Git commit-trailer serializer for MCP-produced commits.

See docs/plans/2026-09-05-comment-view-shared-interfaces-design.md §6."""

from __future__ import annotations

import subprocess
from pathlib import Path


def build_trailers(
    *,
    issue_id: int | str,
    comment_id: str,
    session_id: str,
    revision_from: str,
    revision_to: str,
    model_diff_digest: str,
    provider: str | None = None,
) -> str:
    lines = [
        f"Issue: logs-db#{issue_id}",
        f"Comment: {comment_id}",
        f"Session: {session_id}",
        f"Model-Revision-From: {revision_from}",
        f"Model-Revision-To: {revision_to}",
        f"Model-Diff-Digest: {model_diff_digest}",
    ]
    if provider is not None:
        lines.append(f"Provider: {provider}")
    return "\n".join(lines)


def commit_with_trailers(
    repo_path: Path, *, subject: str, body: str, trailers: str,
) -> str:
    """Runs git add -A + git commit -m; returns resulting SHA."""
    message = subject
    if body:
        message += "\n\n" + body
    message += "\n\n" + trailers + "\n"
    subprocess.run(["git", "-C", str(repo_path), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(repo_path), "commit", "-m", message],
        check=True,
    )
    sha = subprocess.check_output(
        ["git", "-C", str(repo_path), "rev-parse", "HEAD"], text=True,
    ).strip()
    return sha
