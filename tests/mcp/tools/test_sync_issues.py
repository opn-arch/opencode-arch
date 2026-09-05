from pathlib import Path
from datetime import datetime, timezone
import yaml
from architecture_model.comments.models import CommentStub
from architecture_model.comments.store import write_stub, load_stub
from opencode_arch.mcp.tools.sync import _push_comments  # extracted helper
from tests.fixtures.fake_logs_db import FakeLogsDB

def _stub(cid="c-1"):
    return CommentStub(
        comment_id=cid, artifact_id="a", view_id="v", slice_id="s",
        package_id="p", revision="0000001",
        body="hi", author="me",
        created_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )

def test_push_backfills_issue_ref(tmp_path):
    write_stub(tmp_path, _stub())
    with FakeLogsDB() as fake:
        results = _push_comments(tmp_path, fake.client)
    assert len(results) == 1
    assert results[0]["issue_id"] == 1
    reloaded = load_stub(tmp_path, "c-1")
    assert reloaded.issue_ref.issue_id == 1

def test_push_is_idempotent(tmp_path):
    write_stub(tmp_path, _stub())
    with FakeLogsDB() as fake:
        _push_comments(tmp_path, fake.client)
        results2 = _push_comments(tmp_path, fake.client)
    assert results2 == []  # nothing to push second time
