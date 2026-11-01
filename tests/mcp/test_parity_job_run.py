"""Behavioral-parity coverage for the ``arch_job_run`` tool.

Asserts the full ``@arch_tool`` contract: success envelope (completed job +
proposal_ref), observation spans, mining telemetry, the failed-job soft
envelope (``ok: True`` / ``proposal_ref: None`` / ``error``), and the error
taxonomy (invalid arg, repo missing, proposer-config faults, plugin faults,
job missing, not-queued). Behavioral coverage, NOT legacy AMS output-shape
equivalence.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import yaml

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records
from openag.ai.jobs import JobState, JobStore
from openag.ai.work_order import WorkOrder

from opencode_arch.mcp.tools.ai.arch_job_run import arch_job_run

# Make the sibling fixtures module importable as a top-level module so the
# proposer plugin ref '_openag_proposer_fixtures:valid_patch' resolves.
sys.path.insert(0, str(Path(__file__).parent))


def _seed_model(repo: Path) -> None:
    model_dir = repo / ".architecture" / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "root.v3.yaml").write_text(
        yaml.safe_dump(
            {
                "meta": {"schema_version": "0.1"},
                "entities": {
                    "components": [
                        {"id": "C1", "name": "One", "kind": "Component"}
                    ]
                },
                "relationships": [],
            }
        ),
        encoding="utf-8",
    )


def _seed_workorder(repo: Path) -> str:
    wo = WorkOrder.build(
        intent="do a thing",
        slices=[("S1", "0000001")],
        accepts=["model-patch"],
        requested_by="tester",
        max_tokens=1000,
        max_wall_seconds=60,
    )
    wo_dir = repo / ".architecture" / "ai" / "workorders"
    wo_dir.mkdir(parents=True, exist_ok=True)
    (wo_dir / f"{wo.id}.yaml").write_text(
        yaml.safe_dump(wo.to_dict(), sort_keys=True), encoding="utf-8"
    )
    return wo.id


def _queued_job(repo: Path, wo_id: str) -> str:
    store = JobStore(root=repo)
    job = store.create(work_order_id=wo_id)
    store.transition(job.id, JobState.approved)
    store.transition(job.id, JobState.queued)
    return job.id


def _write_config(repo: Path, plugin: str, *, enabled: bool = True) -> None:
    cfg_dir = repo / ".architecture" / "ai"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "proposer_config.yaml").write_text(
        yaml.safe_dump({"plugin": plugin, "enabled": enabled}),
        encoding="utf-8",
    )


def _seed_queued(repo: Path) -> str:
    _seed_model(repo)
    wo_id = _seed_workorder(repo)
    return _queued_job(repo, wo_id)


def test_parity_job_run_completed(tmp_path):
    repo = tmp_path / "happy"
    repo.mkdir(parents=True)

    assert getattr(arch_job_run, "__wrapped__", None) is not None

    job_id = _seed_queued(repo)
    _write_config(repo, "_openag_proposer_fixtures:valid_patch")

    out = asyncio.run(arch_job_run(repo_path=str(repo), job_id=job_id))
    assert out["ok"] is True
    assert out["job"]["state"] == "completed"
    assert out["proposal_ref"] == f".architecture/ai/proposals/{job_id}.yaml"

    records = read_journal(repo)
    in_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_job_run"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "in"
    ]
    out_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_job_run"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_job_run"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_job_run_failed_soft_envelope(tmp_path):
    repo = tmp_path / "failed"
    repo.mkdir(parents=True)
    job_id = _seed_queued(repo)
    _write_config(repo, "_openag_proposer_fixtures:invalid_patch")

    out = asyncio.run(arch_job_run(repo_path=str(repo), job_id=job_id))
    assert out["ok"] is True
    assert out["proposal_ref"] is None
    assert out["job"]["state"] == "failed"
    assert out["error"]


def test_parity_job_run_empty_job_id(tmp_path):
    repo = tmp_path / "badarg"
    repo.mkdir(parents=True)
    out = asyncio.run(arch_job_run(repo_path=str(repo), job_id=""))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_parity_job_run_repo_missing(tmp_path):
    out = asyncio.run(
        arch_job_run(repo_path=str(tmp_path / "nope"), job_id="job-x")
    )
    assert out["ok"] is False
    assert out["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}


def test_parity_job_run_no_proposer_configured(tmp_path):
    repo = tmp_path / "nocfg"
    repo.mkdir(parents=True)
    job_id = _seed_queued(repo)
    out = asyncio.run(arch_job_run(repo_path=str(repo), job_id=job_id))
    assert out["ok"] is False
    assert out["error"]["code"] == "PRECONDITION_FAILED"
    assert out["error"]["details"]["reason"] == "no_proposer_configured"


def test_parity_job_run_proposer_disabled(tmp_path):
    repo = tmp_path / "disabled"
    repo.mkdir(parents=True)
    job_id = _seed_queued(repo)
    _write_config(repo, "_openag_proposer_fixtures:valid_patch", enabled=False)
    out = asyncio.run(arch_job_run(repo_path=str(repo), job_id=job_id))
    assert out["ok"] is False
    assert out["error"]["code"] == "PRECONDITION_FAILED"
    assert out["error"]["details"]["reason"] == "proposer_disabled"


def test_parity_job_run_config_malformed(tmp_path):
    repo = tmp_path / "malformed"
    repo.mkdir(parents=True)
    job_id = _seed_queued(repo)
    cfg_dir = repo / ".architecture" / "ai"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "proposer_config.yaml").write_text(
        yaml.safe_dump({"enabled": True}), encoding="utf-8"  # no 'plugin'
    )
    out = asyncio.run(arch_job_run(repo_path=str(repo), job_id=job_id))
    assert out["ok"] is False
    assert out["error"]["code"] == "PRECONDITION_FAILED"
    assert out["error"]["details"]["reason"] == "proposer_config_malformed"


def test_parity_job_run_plugin_not_loadable(tmp_path):
    repo = tmp_path / "noplugin"
    repo.mkdir(parents=True)
    job_id = _seed_queued(repo)
    _write_config(repo, "nonexistent_module_xyz:func")
    out = asyncio.run(arch_job_run(repo_path=str(repo), job_id=job_id))
    assert out["ok"] is False
    assert out["error"]["code"] == "PRECONDITION_FAILED"
    assert out["error"]["details"]["reason"] == "proposer_plugin_not_loadable"


def test_parity_job_run_plugin_not_callable(tmp_path):
    repo = tmp_path / "notcallable"
    repo.mkdir(parents=True)
    job_id = _seed_queued(repo)
    _write_config(repo, "_openag_proposer_fixtures:NOT_A_FUNCTION")
    out = asyncio.run(arch_job_run(repo_path=str(repo), job_id=job_id))
    assert out["ok"] is False
    assert out["error"]["code"] == "PRECONDITION_FAILED"
    assert out["error"]["details"]["reason"] == "proposer_plugin_not_callable"


def test_parity_job_run_job_missing(tmp_path):
    repo = tmp_path / "jobmissing"
    repo.mkdir(parents=True)
    _seed_model(repo)
    _write_config(repo, "_openag_proposer_fixtures:valid_patch")
    out = asyncio.run(arch_job_run(repo_path=str(repo), job_id="job-nope"))
    assert out["ok"] is False
    assert out["error"]["code"] == "NOT_FOUND"
    assert out["error"]["details"]["reason"] == "job_missing"


def test_parity_job_run_job_not_queued(tmp_path):
    repo = tmp_path / "notqueued"
    repo.mkdir(parents=True)
    _seed_model(repo)
    wo_id = _seed_workorder(repo)
    store = JobStore(root=repo)
    job = store.create(work_order_id=wo_id)  # draft, not queued
    _write_config(repo, "_openag_proposer_fixtures:valid_patch")
    out = asyncio.run(arch_job_run(repo_path=str(repo), job_id=job.id))
    assert out["ok"] is False
    assert out["error"]["code"] == "PRECONDITION_FAILED"
    assert out["error"]["details"]["reason"] == "job_not_queued"
    assert out["error"]["details"]["state"] == "draft"
