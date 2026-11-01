"""Behavioral-parity coverage for the ``arch_job_get`` tool.

Asserts the full ``@arch_tool`` contract: success envelope (job dict), observation
spans, mining telemetry, and the error taxonomy. Behavioral coverage, NOT legacy AMS
output-shape equivalence.
"""
from __future__ import annotations

import asyncio

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records
from openag.ai.jobs import JobStore

from opencode_arch.mcp.tools.ai.arch_job_get import arch_job_get


def test_parity_job_get(tmp_path):
    repo = tmp_path / "happy"
    repo.mkdir(parents=True)

    assert getattr(arch_job_get, "__wrapped__", None) is not None

    seeded = JobStore(root=repo).create(work_order_id="WO-1")

    out = asyncio.run(arch_job_get(repo_path=str(repo), job_id=seeded.id))
    assert out["ok"] is True
    assert out["job"]["id"] == seeded.id
    assert out["job"]["work_order_id"] == "WO-1"
    assert out["job"]["state"] == "draft"

    records = read_journal(repo)
    in_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_job_get"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "in"
    ]
    out_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_job_get"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_job_get"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_job_get_empty_job_id(tmp_path):
    repo = tmp_path / "badarg"
    repo.mkdir(parents=True)
    out = asyncio.run(arch_job_get(repo_path=str(repo), job_id=""))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_parity_job_get_job_missing(tmp_path):
    repo = tmp_path / "jobmissing"
    repo.mkdir(parents=True)
    out = asyncio.run(arch_job_get(repo_path=str(repo), job_id="job-nope"))
    assert out["ok"] is False
    assert out["error"]["code"] == "NOT_FOUND"
    assert out["error"]["details"]["reason"] == "job_missing"


def test_parity_job_get_repo_missing(tmp_path):
    out = asyncio.run(arch_job_get(repo_path=str(tmp_path / "nope"), job_id="job-x"))
    assert out["ok"] is False
    assert out["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}
