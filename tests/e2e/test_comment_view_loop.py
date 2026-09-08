"""End-to-end: comment CLI -> sync -> work_issue -> commit -> close -> journal."""

from __future__ import annotations

import json
import subprocess

from opencode_arch.mcp.tools.sync import _push_comments
from opencode_arch.mcp.tools.work_issue import architect_work_issue
from tests.fixtures.fake_logs_db import FakeLogsDB
from tests.fixtures.repo_fixture import fresh_repo_with_published_generation


def test_full_loop(tmp_path, monkeypatch):
    repo, root_digest = fresh_repo_with_published_generation(tmp_path)
    monkeypatch.setenv("STUB_PROPOSER_MODEL_VERSION", root_digest)
    monkeypatch.setenv("OPENCODE_SESSION_ID", "ses_e2e")

    # Capture: CLI writes stub
    r = subprocess.run(
        [
            "architecture-model", "comment", "art-1",
            "--view-id", "v-1", "--slice-id", "s-1",
            "--package-id", "p-1", "--revision", "0000001",
            "--body", "test", "--author", "tester",
        ],
        cwd=repo, capture_output=True, text=True, check=True,
    )
    comment_id = r.stdout.strip()
    assert comment_id, r.stderr

    with FakeLogsDB() as fake:
        monkeypatch.setenv("LOGS_DB_URL", f"http://127.0.0.1:{fake._port}")

        pushed = _push_comments(repo, fake.client)
        assert pushed
        assert len(fake.issues) == 1
        iid = list(fake.issues.values())[0]["issue_id"]

        env = architect_work_issue(str(repo), issue_id=iid, dry_run=False)

        assert env["ok"] is True, env
        assert env.get("commit_sha"), env

        msg = subprocess.check_output(
            ["git", "-C", str(repo), "log", "-1", "--format=%B"], text=True,
        )
        assert f"Issue: logs-db#{iid}" in msg
        assert f"Comment: {comment_id}" in msg
        assert "Session: ses_e2e" in msg
        assert "Model-Revision-From: 0000001" in msg
        assert "Model-Revision-To: 0000002" in msg
        assert "Model-Diff-Digest: sha256-v1:" in msg

        assert fake.issues[iid]["state"] == "closed"
        assert fake.issues[iid]["close_meta"]["commit_sha"] == env["commit_sha"]

    journal_lines = (repo / ".architecture" / "lifecycle" / "journal.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    events = [json.loads(l)["event"] for l in journal_lines if l.strip()]
    for expected in (
        "comment.capture",
        "comment.sync",
        "issue.pull",
        "workorder.from_issue",
        "issue.close",
    ):
        assert expected in events, (expected, events)
