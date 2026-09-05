from pathlib import Path
from datetime import datetime, timezone
from architecture_model.comments.models import CommentStub
from architecture_model.comments.store import write_stub, set_issue_ref
from architecture_model.comments.models import IssueRef
from tests.fixtures.fake_logs_db import FakeLogsDB
from opencode_arch.mcp.tools.work_issue import _load_and_resolve, WorkIssueError


def _stub(cid="c-1"):
    return CommentStub(
        comment_id=cid, artifact_id="a", view_id="v", slice_id="s",
        package_id="p", revision="0000001",
        body="body", author="me",
        created_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )


def test_load_and_resolve_happy(tmp_path, monkeypatch):
    write_stub(tmp_path, _stub())
    with FakeLogsDB() as fake:
        r = fake.client.create_issue(
            external_key="c-1", title="t", body="b", tags=[], meta={},
        )
        set_issue_ref(tmp_path, "c-1", IssueRef(issue_id=r["issue_id"]))
        ctx = _load_and_resolve(tmp_path, fake.client, r["issue_id"])
    assert ctx.stub.comment_id == "c-1"
    assert ctx.issue["state"] == "open"


def test_load_and_resolve_missing_stub_raises(tmp_path):
    with FakeLogsDB() as fake:
        r = fake.client.create_issue(
            external_key="unknown-id", title="t", body="b", tags=[], meta={},
        )
        try:
            _load_and_resolve(tmp_path, fake.client, r["issue_id"])
        except WorkIssueError as e:
            assert "stub" in str(e).lower()
        else:
            raise AssertionError("expected WorkIssueError")
