from pathlib import Path
from datetime import datetime, timezone
import yaml
from architecture_model.comments.models import CommentStub
from architecture_model.comments.store import write_stub, set_issue_ref
from architecture_model.comments.models import IssueRef
from architecture_model.lifecycle.package import load_package
from architecture_model.lifecycle.publication import PackageBundle, publish
from architecture_model.lifecycle.versions import SchemaVersions
from tests.fixtures.fake_logs_db import FakeLogsDB
from opencode_arch.mcp.tools.work_issue import _load_and_resolve, WorkIssueError


_MODEL_YAML = (
    "meta:\n"
    "  schema_version: '1.3'\n"
    "  project: test\n"
    "entities:\n"
    "  components:\n"
    "    - id: COMP-1\n"
    "      name: Alpha\n"
    "      status: ACTIVE\n"
)


def _publish_root(repo):
    lifecycle = repo / ".architecture" / "lifecycle"
    lifecycle.mkdir(parents=True, exist_ok=True)
    (lifecycle / "package.yaml").write_text(
        yaml.safe_dump({
            "architecture_id": "root",
            "name": "root",
            "slug": "root",
            "contract_version": SchemaVersions.PACKAGE,
            "model_ref": "model/.architecture-model.yaml",
            "manifest_ref": "manifest/manifest.json",
        }, sort_keys=True),
        encoding="utf-8",
    )
    pkg = load_package(lifecycle)
    res = publish(pkg, PackageBundle(model_bytes=_MODEL_YAML.encode(), manifest_bytes=b"{}"))
    return pkg, res


def _setup_ctx(tmp_path, fake_client, *, comment_id="c-1", revision="0000001"):
    stub = CommentStub(
        comment_id=comment_id, artifact_id="a", view_id="v", slice_id="s",
        package_id="p", revision=revision,
        body="please add COMP-3", author="tester",
        created_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )
    write_stub(tmp_path, stub)
    issue_res = fake_client.create_issue(
        external_key=comment_id, title="t", body="b", tags=[], meta={},
    )
    set_issue_ref(tmp_path, comment_id, IssueRef(issue_id=issue_res["issue_id"]))
    return _load_and_resolve(tmp_path, fake_client, issue_res["issue_id"])


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


def test_submit_run_apply_success_dry_run(tmp_path, monkeypatch):
    from opencode_arch.mcp.tools.work_issue import _submit_run_validate_apply, _workorder_from_stub
    from tests.fixtures.fake_proposer import make_noop_valid_proposer

    monkeypatch.setenv("OPENCODE_SESSION_ID", "ses_test")
    _, res = _publish_root(tmp_path)

    with FakeLogsDB() as fake:
        ctx = _setup_ctx(tmp_path, fake.client)
        wo = _workorder_from_stub(stub=ctx.stub, issue_id=ctx.issue["issue_id"],
                                  issue_url=ctx.issue.get("url", ""))
        proposer = make_noop_valid_proposer(model_version=res.root_digest)
        env = _submit_run_validate_apply(ctx, wo, client=fake.client,
                                         proposer=proposer, dry_run=True)

    assert env["ok"] is True, env
    assert env["work_order_id"] == wo.id
    assert env["commit_sha"] is None
    assert env["dry_run"] is True
    assert env["package_revision_to"] is None
    assert env["model_diff_digest"] is None


def test_submit_run_apply_invalid_proposal_posts_comment(tmp_path, monkeypatch):
    from opencode_arch.mcp.tools.work_issue import _submit_run_validate_apply, _workorder_from_stub
    from tests.fixtures.fake_proposer import make_invalid_proposer

    monkeypatch.setenv("OPENCODE_SESSION_ID", "ses_test")
    _publish_root(tmp_path)

    with FakeLogsDB() as fake:
        ctx = _setup_ctx(tmp_path, fake.client)
        wo = _workorder_from_stub(stub=ctx.stub, issue_id=ctx.issue["issue_id"],
                                  issue_url=ctx.issue.get("url", ""))
        env = _submit_run_validate_apply(ctx, wo, client=fake.client,
                                         proposer=make_invalid_proposer(), dry_run=True)
        issue = fake.client.get_issue(ctx.issue["issue_id"])

    assert env["ok"] is False
    assert env["error"] == "proposal_invalid"
    assert "job_id" in env
    assert len(issue["comments"]) >= 1
    assert issue["comments"][0]["author"] == "mcp"


def test_architect_work_issue_dry_run_envelope(tmp_path, monkeypatch):
    """End-to-end envelope: full tool wrapper with fake proposer via kwarg."""
    from opencode_arch.mcp.tools.work_issue import architect_work_issue
    from tests.fixtures.fake_proposer import make_noop_valid_proposer

    monkeypatch.setenv("OPENCODE_SESSION_ID", "ses_env_test")
    _, res = _publish_root(tmp_path)

    with FakeLogsDB() as fake:
        monkeypatch.setenv("LOGS_DB_URL", f"http://127.0.0.1:{fake._port}")
        ctx = _setup_ctx(tmp_path, fake.client, comment_id="c-env")
        iid = ctx.issue["issue_id"]
        env = architect_work_issue(
            str(tmp_path),
            issue_id=iid,
            dry_run=True,
            proposer=make_noop_valid_proposer(model_version=res.root_digest),
        )

    assert env["ok"] is True, env
    assert "work_order_id" in env
    assert env["commit_sha"] is None
    assert env.get("dry_run") is True


def test_architect_work_issue_reuses_prior_completed_job(tmp_path, monkeypatch):
    """Second call with same comment short-circuits when a completed Job exists."""
    from opencode_arch.mcp.tools.work_issue import architect_work_issue
    from tests.fixtures.fake_proposer import make_noop_valid_proposer

    monkeypatch.setenv("OPENCODE_SESSION_ID", "ses_reuse")
    _, res = _publish_root(tmp_path)
    proposer = make_noop_valid_proposer(model_version=res.root_digest)

    with FakeLogsDB() as fake:
        monkeypatch.setenv("LOGS_DB_URL", f"http://127.0.0.1:{fake._port}")
        ctx = _setup_ctx(tmp_path, fake.client, comment_id="c-reuse")
        iid = ctx.issue["issue_id"]
        first = architect_work_issue(str(tmp_path), issue_id=iid, dry_run=True, proposer=proposer)
        second = architect_work_issue(str(tmp_path), issue_id=iid, dry_run=True, proposer=proposer)

    assert first["ok"] is True
    assert second.get("reused") is True
    assert second["work_order_id"] == first["work_order_id"]
