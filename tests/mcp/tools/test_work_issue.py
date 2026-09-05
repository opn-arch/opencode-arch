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


def test_workorder_from_stub_populates_parameters(tmp_path, monkeypatch):
    from opencode_arch.mcp.tools.work_issue import _workorder_from_stub
    monkeypatch.setenv("OPENCODE_SESSION_ID", "ses_xyz")
    stub = _stub()
    wo = _workorder_from_stub(stub=stub, issue_id=42, issue_url="http://x/42")
    assert wo.requested_by == "logs-db#42"
    assert wo.parameters["issue_id"] == 42
    assert wo.parameters["comment_id"] == "c-1"
    assert wo.parameters["session_id"] == "ses_xyz"
    assert wo.input_slice_refs and wo.input_slice_refs[0].slice_id == "s"


def test_existing_completed_job_short_circuits(tmp_path):
    """Completed Job whose WorkOrder.parameters.comment_id matches must be returned."""
    from architecture_model.ai.jobs import JobStore, JobState
    from architecture_model.ai.work_order import WorkOrder, SliceRef
    from architecture_model.lifecycle.atomic_store import write_atomic
    from opencode_arch.mcp.tools.work_issue import _existing_completed_job
    import yaml

    # 1. Build + persist a WorkOrder carrying comment_id in parameters.
    wo = WorkOrder.build(
        intent="x",
        slices=[SliceRef(slice_id="s", model_revision="0000001")],
        accepts=["model-patch"],
        max_tokens=1000, max_wall_seconds=60,
        requested_by="test",
        parameters={"comment_id": "c-1"},
    )
    wo_dir = tmp_path / ".architecture" / "ai" / "workorders"
    wo_dir.mkdir(parents=True, exist_ok=True)
    write_atomic(wo_dir / f"{wo.id}.yaml", yaml.safe_dump(wo.to_dict()).encode("utf-8"))

    # 2. Create Job, transition draft→approved→queued→running→validating→completed.
    js = JobStore(tmp_path)
    job = js.create(work_order_id=wo.id)
    js.transition(job.id, JobState.approved)
    js.transition(job.id, JobState.queued)
    js.transition(job.id, JobState.running)
    js.transition(job.id, JobState.validating)
    js.transition(job.id, JobState.completed, result_ref="prop-1")

    # 3. Look up.
    found = _existing_completed_job(tmp_path, comment_id="c-1")
    assert found is not None
    assert found.id == job.id

    # 4. Different comment_id returns None.
    assert _existing_completed_job(tmp_path, comment_id="other") is None
