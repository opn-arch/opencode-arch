"""Tests for architect_proposal_apply MCP tool (T19)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
import yaml

from architecture_model.ai.jobs import JobState, JobStore
from architecture_model.lifecycle.package import load_package
from architecture_model.lifecycle.publication import PackageBundle, publish
from architecture_model.lifecycle.versions import SchemaVersions


ROOT_ID = "root-pkg"
WO_ID = "wo-t19-001"
PROMPT_DIGEST = "sha256:aaa"

MODEL_YAML = (
    "meta:\n"
    "  project: t\n"
    "  schema_version: '1.3'\n"
    "entities:\n"
    "  components:\n"
    "    - id: COMP-1\n"
    "      name: Alpha\n"
    "      status: ACTIVE\n"
    "    - id: COMP-2\n"
    "      name: Beta\n"
    "      status: ACTIVE\n"
)


def _run(coro):
    return asyncio.run(coro)


def _write_root_package(repo: Path) -> Path:
    lifecycle = repo / ".architecture" / "lifecycle"
    lifecycle.mkdir(parents=True, exist_ok=True)
    (lifecycle / "package.yaml").write_text(
        yaml.safe_dump(
            {
                "architecture_id": ROOT_ID,
                "name": "Root",
                "slug": ROOT_ID,
                "contract_version": SchemaVersions.PACKAGE,
                "model_ref": "model/.architecture-model.yaml",
                "manifest_ref": "manifest/manifest.json",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return lifecycle


def _publish_initial(repo: Path):
    lifecycle = _write_root_package(repo)
    pkg = load_package(lifecycle)
    result = publish(
        pkg,
        PackageBundle(
            model_bytes=MODEL_YAML.encode("utf-8"), manifest_bytes=b"{}"
        ),
    )
    return pkg, result


def _write_workorder(repo: Path, wo_id: str = WO_ID) -> None:
    wo_dir = repo / ".architecture" / "ai" / "workorders"
    wo_dir.mkdir(parents=True, exist_ok=True)
    (wo_dir / f"{wo_id}.yaml").write_text(
        yaml.safe_dump(
            {
                "id": wo_id,
                "intent": "test",
                "input_slice_refs": [
                    {"slice_id": "slice-1", "model_revision": "rev-1"}
                ],
                "expected_proposal_kinds": ["model-patch"],
                "budget": {"max_tokens": 1000, "max_wall_seconds": 60},
                "requested_by": "tester",
                "created_at": "2026-09-04T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )


def _model_patch_dict(model_version: str) -> dict:
    return {
        "kind": "model-patch",
        "provenance": {
            "work_order_id": WO_ID,
            "model_version": model_version,
            "prompt_digest": PROMPT_DIGEST,
        },
        "operations": [{"op": "remove", "target_id": "COMP-2"}],
    }


def _slice_proposal_dict(model_version: str = "any") -> dict:
    return {
        "kind": "slice-proposal",
        "provenance": {
            "work_order_id": WO_ID,
            "model_version": model_version,
            "prompt_digest": PROMPT_DIGEST,
        },
        "slice": {"id": "slice-new", "fragment": {}},
    }


def _persist_proposal(
    repo: Path, job_id: str, proposal: dict
) -> str:
    """Write proposal YAML and return posix-relative result_ref."""
    p_dir = repo / ".architecture" / "ai" / "proposals"
    p_dir.mkdir(parents=True, exist_ok=True)
    path = p_dir / f"{job_id}.yaml"
    path.write_text(
        yaml.safe_dump(proposal, sort_keys=True), encoding="utf-8"
    )
    return path.relative_to(repo).as_posix()


def _make_completed_job(
    repo: Path, proposal: dict, *, wo_id: str = WO_ID
) -> str:
    """Create a job and drive it to `completed` state with persisted proposal."""
    store = JobStore(root=repo)
    job = store.create(work_order_id=wo_id)
    store.transition(job.id, JobState.approved, actor="tester")
    store.transition(job.id, JobState.queued, actor="tester")
    store.transition(job.id, JobState.running, actor="tester")
    store.transition(job.id, JobState.validating, actor="tester")
    ref = _persist_proposal(repo, job.id, proposal)
    store.transition(
        job.id, JobState.completed, actor="tester", result_ref=ref
    )
    return job.id


def _setup_full(repo: Path, proposal_dict: dict) -> str:
    """Setup lifecycle + WO + completed job; returns job_id."""
    _publish_initial(repo)
    _write_workorder(repo)
    return _make_completed_job(repo, proposal_dict)


@pytest.fixture
def apply_tool():
    from opencode_arch.mcp.tools.ai.proposal_apply import (
        architect_proposal_apply_tool,
    )

    return architect_proposal_apply_tool


# ---------------------------------------------------------------- happy paths


def test_happy_dry_run_model_patch(tmp_path, apply_tool):
    _, res = _publish_initial(tmp_path)
    proposal = _model_patch_dict(res.root_digest)
    _write_workorder(tmp_path)
    job_id = _make_completed_job(tmp_path, proposal)

    env = _run(
        apply_tool(
            repo_path=str(tmp_path),
            proposal=proposal,
            work_order_id=WO_ID,
            dry_run=True,
        )
    )
    assert env["ok"] is True
    assert env["report"]["new_revision"] is None
    assert env["report"]["digest"] is None
    assert env["report"]["changes"][0]["op"] == "remove"
    # Dry run must NOT write the T19 journal event.
    jpath = tmp_path / ".architecture" / "lifecycle" / "journal.jsonl"
    if jpath.exists():
        events = [
            json.loads(l)["event"]
            for l in jpath.read_text(encoding="utf-8").splitlines()
            if l
        ]
        assert "ai.proposal.apply" not in events


def test_happy_non_dry_model_patch_publishes_and_journals(tmp_path, apply_tool):
    _, res = _publish_initial(tmp_path)
    proposal = _model_patch_dict(res.root_digest)
    _write_workorder(tmp_path)
    job_id = _make_completed_job(tmp_path, proposal)

    env = _run(
        apply_tool(
            repo_path=str(tmp_path),
            proposal=proposal,
            work_order_id=WO_ID,
            dry_run=False,
        )
    )
    assert env["ok"] is True
    assert env["report"]["new_revision"] == "0000002"
    assert env["report"]["digest"] and env["report"]["digest"] != res.root_digest
    # Must be JSON-serializable.
    json.dumps(env)
    # Journal has the T19 event with expected payload.
    jpath = tmp_path / ".architecture" / "lifecycle" / "journal.jsonl"
    events = [
        json.loads(l)
        for l in jpath.read_text(encoding="utf-8").splitlines()
        if l
    ]
    top = [e for e in events if e["event"] == "ai.proposal.apply"]
    assert len(top) == 1
    payload = top[0]["payload"]
    assert payload["work_order_id"] == WO_ID
    assert payload["job_id"] == job_id
    assert payload["dry_run"] is False
    assert payload["ok"] is True
    assert payload["new_revision"] == "0000002"
    assert payload["digest"] == env["report"]["digest"]
    assert payload["kind"] == "model-patch"


def test_happy_slice_proposal_new_revision_none(tmp_path, apply_tool):
    _publish_initial(tmp_path)
    proposal = _slice_proposal_dict()
    _write_workorder(tmp_path)
    _make_completed_job(tmp_path, proposal)

    env = _run(
        apply_tool(
            repo_path=str(tmp_path),
            proposal=proposal,
            work_order_id=WO_ID,
            dry_run=False,
        )
    )
    assert env["ok"] is True
    assert env["report"]["new_revision"] is None
    assert env["report"]["digest"] is None
    # slice file persisted.
    assert (
        tmp_path
        / ".architecture"
        / "lifecycle"
        / "slices"
        / "slice-new.yaml"
    ).exists()
    # T19 journal event still written for slice kind.
    jpath = tmp_path / ".architecture" / "lifecycle" / "journal.jsonl"
    events = [
        json.loads(l)
        for l in jpath.read_text(encoding="utf-8").splitlines()
        if l
    ]
    top = [e for e in events if e["event"] == "ai.proposal.apply"]
    assert len(top) == 1
    assert top[0]["payload"]["kind"] == "slice-proposal"
    assert top[0]["payload"]["new_revision"] is None
    assert top[0]["payload"]["digest"] is None


# ---------------------------------------------------------------- preconditions


def test_workorder_missing(tmp_path, apply_tool):
    _publish_initial(tmp_path)
    proposal = _slice_proposal_dict()
    env = _run(
        apply_tool(
            repo_path=str(tmp_path),
            proposal=proposal,
            work_order_id=WO_ID,
            dry_run=True,
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "PRECONDITION_FAILED"
    assert env["error"]["details"]["reason"] == "workorder_missing"


def test_job_missing(tmp_path, apply_tool):
    _publish_initial(tmp_path)
    _write_workorder(tmp_path)
    proposal = _slice_proposal_dict()
    env = _run(
        apply_tool(
            repo_path=str(tmp_path),
            proposal=proposal,
            work_order_id=WO_ID,
            dry_run=True,
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "PRECONDITION_FAILED"
    assert env["error"]["details"]["reason"] == "job_missing"


def test_job_not_completed(tmp_path, apply_tool):
    _publish_initial(tmp_path)
    _write_workorder(tmp_path)
    proposal = _slice_proposal_dict()
    # Job in `running` state.
    store = JobStore(root=tmp_path)
    j = store.create(work_order_id=WO_ID)
    store.transition(j.id, JobState.approved)
    store.transition(j.id, JobState.queued)
    store.transition(j.id, JobState.running)

    env = _run(
        apply_tool(
            repo_path=str(tmp_path),
            proposal=proposal,
            work_order_id=WO_ID,
            dry_run=True,
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "PRECONDITION_FAILED"
    assert env["error"]["details"]["reason"] == "job_not_completed"
    assert env["error"]["details"]["state"] == "running"


def test_proposal_identity_mismatch(tmp_path, apply_tool):
    _publish_initial(tmp_path)
    _write_workorder(tmp_path)
    persisted = _slice_proposal_dict()
    _make_completed_job(tmp_path, persisted)

    # Caller sends a DIFFERENT prompt_digest.
    mismatch = _slice_proposal_dict()
    mismatch["provenance"]["prompt_digest"] = "sha256:different"

    env = _run(
        apply_tool(
            repo_path=str(tmp_path),
            proposal=mismatch,
            work_order_id=WO_ID,
            dry_run=True,
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "PRECONDITION_FAILED"
    assert env["error"]["details"]["reason"] == "proposal_mismatch"


# ---------------------------------------------------------------- schema violations


def test_malformed_proposal_dict(tmp_path, apply_tool):
    _publish_initial(tmp_path)
    _write_workorder(tmp_path)
    # No job needed — even before precondition check, a proposal dict lacking
    # provenance can't be identity-matched. Whichever gate fires first, the
    # envelope must be a well-formed error.
    bad = {"kind": "slice-proposal"}
    env = _run(
        apply_tool(
            repo_path=str(tmp_path),
            proposal=bad,
            work_order_id=WO_ID,
            dry_run=True,
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] in {"SCHEMA_VIOLATION", "PRECONDITION_FAILED"}


def test_malformed_proposal_after_identity_ok(
    tmp_path, apply_tool, monkeypatch
):
    """Force the schema-violation branch by making identity check pass then
    parse fail. We do this by monkeypatching proposal_from_dict to raise."""
    _publish_initial(tmp_path)
    _write_workorder(tmp_path)
    persisted = _slice_proposal_dict()
    _make_completed_job(tmp_path, persisted)

    from architecture_model.ai import proposals as prop_mod

    def _boom(_data):
        raise KeyError("provenance")

    monkeypatch.setattr(prop_mod, "proposal_from_dict", _boom)

    env = _run(
        apply_tool(
            repo_path=str(tmp_path),
            proposal=persisted,
            work_order_id=WO_ID,
            dry_run=True,
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "SCHEMA_VIOLATION"


# ---------------------------------------------------------------- exception mapping


def test_drift_error_maps_to_precondition(tmp_path, apply_tool, monkeypatch):
    _publish_initial(tmp_path)
    _write_workorder(tmp_path)
    persisted = _slice_proposal_dict()
    _make_completed_job(tmp_path, persisted)

    from opencode_arch.lifecycle_exec import apply as apply_mod
    from opencode_arch.mcp.tools.ai import proposal_apply as tool_mod

    def _raise(*a, **kw):
        raise apply_mod.DriftError(expected="EXP", actual="ACT")

    monkeypatch.setattr(tool_mod, "apply_proposal", _raise)

    env = _run(
        apply_tool(
            repo_path=str(tmp_path),
            proposal=persisted,
            work_order_id=WO_ID,
            dry_run=True,
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "PRECONDITION_FAILED"
    assert env["error"]["details"]["expected"] == "EXP"
    assert env["error"]["details"]["actual"] == "ACT"


def test_invalid_proposal_error_maps_to_schema(tmp_path, apply_tool, monkeypatch):
    _publish_initial(tmp_path)
    _write_workorder(tmp_path)
    persisted = _slice_proposal_dict()
    _make_completed_job(tmp_path, persisted)

    from opencode_arch.lifecycle_exec import apply as apply_mod
    from opencode_arch.mcp.tools.ai import proposal_apply as tool_mod

    def _raise(*a, **kw):
        raise apply_mod.InvalidProposalError("duplicate id COMP-1")

    monkeypatch.setattr(tool_mod, "apply_proposal", _raise)

    env = _run(
        apply_tool(
            repo_path=str(tmp_path),
            proposal=persisted,
            work_order_id=WO_ID,
            dry_run=True,
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "SCHEMA_VIOLATION"
    assert "duplicate id COMP-1" in env["error"]["details"]["reason"]


def test_package_not_found_maps_to_not_found(tmp_path, apply_tool, monkeypatch):
    _publish_initial(tmp_path)
    _write_workorder(tmp_path)
    persisted = _slice_proposal_dict()
    _make_completed_job(tmp_path, persisted)

    from opencode_arch.lifecycle_exec import apply as apply_mod
    from opencode_arch.mcp.tools.ai import proposal_apply as tool_mod

    def _raise(*a, **kw):
        raise apply_mod.PackageNotFoundError("no package")

    monkeypatch.setattr(tool_mod, "apply_proposal", _raise)

    env = _run(
        apply_tool(
            repo_path=str(tmp_path),
            proposal=persisted,
            work_order_id=WO_ID,
            dry_run=True,
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert "no package" in env["error"]["details"]["reason"]


def test_unexpected_exception_maps_to_internal(tmp_path, apply_tool, monkeypatch):
    _publish_initial(tmp_path)
    _write_workorder(tmp_path)
    persisted = _slice_proposal_dict()
    _make_completed_job(tmp_path, persisted)

    from opencode_arch.mcp.tools.ai import proposal_apply as tool_mod

    def _raise(*a, **kw):
        raise RuntimeError("boom-stack-line-secret")

    monkeypatch.setattr(tool_mod, "apply_proposal", _raise)

    env = _run(
        apply_tool(
            repo_path=str(tmp_path),
            proposal=persisted,
            work_order_id=WO_ID,
            dry_run=True,
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "INTERNAL"
    # Message contains type name + str(exc) but should NOT contain multi-line
    # stack. Assert message is a single line.
    assert "\n" not in env["error"]["message"]


def test_error_paths_do_not_write_journal(tmp_path, apply_tool, monkeypatch):
    _publish_initial(tmp_path)
    _write_workorder(tmp_path)
    persisted = _slice_proposal_dict()
    _make_completed_job(tmp_path, persisted)

    from opencode_arch.lifecycle_exec import apply as apply_mod
    from opencode_arch.mcp.tools.ai import proposal_apply as tool_mod

    def _raise(*a, **kw):
        raise apply_mod.DriftError(expected="X", actual="Y")

    monkeypatch.setattr(tool_mod, "apply_proposal", _raise)

    # Snapshot journal contents (from _publish_initial there IS a journal).
    jpath = tmp_path / ".architecture" / "lifecycle" / "journal.jsonl"
    before = jpath.read_text(encoding="utf-8") if jpath.exists() else ""

    env = _run(
        apply_tool(
            repo_path=str(tmp_path),
            proposal=persisted,
            work_order_id=WO_ID,
            dry_run=False,
        )
    )
    assert env["ok"] is False
    after = jpath.read_text(encoding="utf-8") if jpath.exists() else ""
    # No new lines added.
    assert after == before


# ---------------------------------------------------------------- serialization + registration


def test_response_is_json_serializable(tmp_path, apply_tool):
    _publish_initial(tmp_path)
    _write_workorder(tmp_path)
    proposal = _slice_proposal_dict()
    _make_completed_job(tmp_path, proposal)

    env = _run(
        apply_tool(
            repo_path=str(tmp_path),
            proposal=proposal,
            work_order_id=WO_ID,
            dry_run=True,
        )
    )
    # Must round-trip through JSON.
    encoded = json.dumps(env)
    assert '"changes"' in encoded


def test_server_registers_proposal_apply():
    """architect_proposal_apply must be importable via the server module."""
    from opencode_arch.mcp import server as server_mod

    # Tool factory function is imported inside the try/except block; simply
    # importing the server module should not raise. Additionally the tool
    # implementation must be importable.
    from opencode_arch.mcp.tools.ai.proposal_apply import (
        architect_proposal_apply_tool,
    )

    assert callable(architect_proposal_apply_tool)
    assert hasattr(server_mod, "mcp")
