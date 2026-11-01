"""Behavioral-parity coverage for the ``arch_job_transition`` tool.

Asserts the full ``@arch_tool`` contract: success envelope, observation spans, mining
telemetry, and the error taxonomy (invalid arg, job missing, illegal transition,
terminal-field guard). Behavioral coverage, NOT legacy AMS output-shape equivalence.
"""
from __future__ import annotations

import asyncio

from openag.observe.journal import read as read_journal
from openag.mining.reservoir import load_records
from openag.ai.jobs import JobState, JobStore

from opencode_arch.mcp.tools.ai.arch_job_transition import arch_job_transition


def _seed_draft(repo) -> str:
    return JobStore(root=repo).create(work_order_id="WO-1").id


def test_parity_job_transition(tmp_path):
    repo = tmp_path / "happy"
    repo.mkdir(parents=True)

    assert getattr(arch_job_transition, "__wrapped__", None) is not None

    job_id = _seed_draft(repo)
    out = asyncio.run(
        arch_job_transition(repo_path=str(repo), job_id=job_id, new_state="approved")
    )
    assert out["ok"] is True
    assert out["job"]["state"] == "approved"

    records = read_journal(repo)
    in_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_job_transition"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "in"
    ]
    out_spans = [
        r for r in records
        if r.get("component_id") == "tool:arch_job_transition"
        and r.get("io_kind") == "tool_call" and r.get("direction") == "out"
    ]
    assert in_spans, f"no in span in {records!r}"
    assert out_spans, f"no out span in {records!r}"

    telemetry = load_records(
        str(repo / ".architecture" / "reservoir" / "tool_telemetry.jsonl")
    )
    drecords = [r for r in telemetry if r.get("tool") == "arch_job_transition"]
    assert len(drecords) == 1, f"expected 1 telemetry record, got {drecords!r}"
    assert drecords[0]["outcome"] == "ok"


def test_parity_job_transition_empty_job_id(tmp_path):
    repo = tmp_path / "badarg"
    repo.mkdir(parents=True)
    out = asyncio.run(arch_job_transition(repo_path=str(repo), job_id="", new_state="approved"))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_parity_job_transition_unknown_state(tmp_path):
    repo = tmp_path / "badstate"
    repo.mkdir(parents=True)
    job_id = _seed_draft(repo)
    out = asyncio.run(
        arch_job_transition(repo_path=str(repo), job_id=job_id, new_state="bogus")
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"
    assert "approved" in out["error"]["details"]["valid_states"]


def test_parity_job_transition_job_missing(tmp_path):
    repo = tmp_path / "jobmissing"
    repo.mkdir(parents=True)
    out = asyncio.run(
        arch_job_transition(repo_path=str(repo), job_id="job-nope", new_state="approved")
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "NOT_FOUND"
    assert out["error"]["details"]["reason"] == "job_missing"


def test_parity_job_transition_illegal(tmp_path):
    repo = tmp_path / "illegal"
    repo.mkdir(parents=True)
    job_id = _seed_draft(repo)  # draft -> running is illegal
    out = asyncio.run(
        arch_job_transition(repo_path=str(repo), job_id=job_id, new_state="running")
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "PRECONDITION_FAILED"
    assert out["error"]["details"]["from_state"] == "draft"
    assert out["error"]["details"]["to_state"] == "running"
    assert "approved" in out["error"]["details"]["allowed"]


def test_parity_job_transition_completed_requires_result_ref(tmp_path):
    repo = tmp_path / "terminal"
    repo.mkdir(parents=True)
    store = JobStore(root=repo)
    job_id = store.create(work_order_id="WO-1").id
    store.transition(job_id, JobState.approved)
    store.transition(job_id, JobState.queued)
    store.transition(job_id, JobState.running)
    store.transition(job_id, JobState.validating)
    # validating -> completed WITHOUT result_ref is an INVALID_ARGUMENT.
    out = asyncio.run(
        arch_job_transition(repo_path=str(repo), job_id=job_id, new_state="completed")
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_parity_job_transition_completed_with_result_ref(tmp_path):
    repo = tmp_path / "terminalok"
    repo.mkdir(parents=True)
    store = JobStore(root=repo)
    job_id = store.create(work_order_id="WO-1").id
    store.transition(job_id, JobState.approved)
    store.transition(job_id, JobState.queued)
    store.transition(job_id, JobState.running)
    store.transition(job_id, JobState.validating)
    out = asyncio.run(
        arch_job_transition(
            repo_path=str(repo),
            job_id=job_id,
            new_state="completed",
            result_ref="proposal:abc",
        )
    )
    assert out["ok"] is True
    assert out["job"]["state"] == "completed"
    assert out["job"]["result_ref"] == "proposal:abc"


def test_parity_job_transition_repo_missing(tmp_path):
    out = asyncio.run(
        arch_job_transition(repo_path=str(tmp_path / "nope"), job_id="job-x", new_state="approved")
    )
    assert out["ok"] is False
    assert out["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT"}
