"""Behavioral-parity coverage for the ``arch_workorder_submit`` tool.

Asserts the full ``@arch_tool`` contract: success envelope (work_order_id + job_id,
persisted WorkOrder, draft Job), observation spans, mining telemetry, and the error
taxonomy. Behavioral coverage, NOT legacy AMS output-shape equivalence.
"""
from __future__ import annotations

import asyncio

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records
from openag.ai.work_order import WorkOrder
from openag.ai.jobs import JobStore, JobState

from opencode_arch.mcp.tools.ai.arch_workorder_submit import arch_workorder_submit


def _valid_wo_dict() -> dict:
    return WorkOrder.build(
        intent="do the thing",
        slices=[("SL-1", "0000001")],
        accepts=["model-patch"],
        requested_by="tester",
        max_tokens=1000,
        max_wall_seconds=60,
    ).to_dict()


def test_parity_workorder_submit(tmp_path):
    repo = tmp_path / "happy"
    repo.mkdir(parents=True)

    assert getattr(arch_workorder_submit, "__wrapped__", None) is not None

    wo_dict = _valid_wo_dict()
    out = asyncio.run(arch_workorder_submit(repo_path=str(repo), work_order=wo_dict))
    assert out["ok"] is True
    assert out["work_order_id"] == wo_dict["id"]
    assert out["job_id"]

    assert (repo / ".architecture" / "ai" / "workorders" / f"{wo_dict['id']}.yaml").exists()

    job = JobStore(root=repo).get(out["job_id"])
    assert job.state == JobState.draft
    assert job.work_order_id == wo_dict["id"]

    records = read_journal(repo)
    in_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_workorder_submit"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "in"
    ]
    out_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_workorder_submit"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_workorder_submit"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_workorder_submit_not_a_dict(tmp_path):
    repo = tmp_path / "badarg"
    repo.mkdir(parents=True)
    out = asyncio.run(arch_workorder_submit(repo_path=str(repo), work_order=None))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_parity_workorder_submit_repo_missing(tmp_path):
    out = asyncio.run(
        arch_workorder_submit(repo_path=str(tmp_path / "nope"), work_order=_valid_wo_dict())
    )
    assert out["ok"] is False
    assert out["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}


def test_parity_workorder_submit_schema_violation(tmp_path):
    repo = tmp_path / "schema"
    repo.mkdir(parents=True)
    bad = _valid_wo_dict()
    del bad["intent"]
    out = asyncio.run(arch_workorder_submit(repo_path=str(repo), work_order=bad))
    assert out["ok"] is False
    assert out["error"]["code"] == "SCHEMA_VIOLATION"
    assert out["error"]["details"]["errors"]


def test_parity_workorder_submit_idempotent_guard(tmp_path):
    repo = tmp_path / "dup"
    repo.mkdir(parents=True)
    wo = _valid_wo_dict()
    first = asyncio.run(arch_workorder_submit(repo_path=str(repo), work_order=wo))
    assert first["ok"] is True
    second = asyncio.run(arch_workorder_submit(repo_path=str(repo), work_order=wo))
    assert second["ok"] is False
    assert second["error"]["code"] == "PRECONDITION_FAILED"
    assert second["error"]["details"]["reason"] == "already_exists"
