"""Tests for architect_workorder_submit MCP tool (T13)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
import yaml


def _run(coro):
    return asyncio.run(coro)


def _valid_wo(wo_id: str = "wo-test-001") -> dict:
    return {
        "id": wo_id,
        "intent": "Add caching to view resolution",
        "input_slice_refs": [
            {"slice_id": "slice-1", "model_revision": "0000001"}
        ],
        "expected_proposal_kinds": ["model-patch"],
        "budget": {"max_tokens": 1000, "max_wall_seconds": 60},
        "requested_by": "user@example.com",
        "created_at": "2026-09-04T00:00:00+00:00",
    }


@pytest.fixture
def submit():
    from opencode_arch.mcp.tools.ai.workorder_submit import (
        architect_workorder_submit_tool,
    )

    return architect_workorder_submit_tool


def test_happy_path(tmp_path: Path, submit) -> None:
    wo = _valid_wo()
    env = _run(submit(repo_path=str(tmp_path), work_order=wo))
    assert env["ok"] is True, env
    assert env["work_order_id"] == "wo-test-001"
    assert env["job_id"].startswith("job-")

    yaml_path = tmp_path / ".architecture" / "ai" / "workorders" / "wo-test-001.yaml"
    assert yaml_path.exists()

    from architecture_model.ai.jobs import JobStore, JobState

    store = JobStore(root=tmp_path)
    job = store.get(env["job_id"])
    assert job.state == JobState.draft
    assert job.work_order_id == "wo-test-001"


def test_journal_event_recorded(tmp_path: Path, submit) -> None:
    wo = _valid_wo()
    env = _run(submit(repo_path=str(tmp_path), work_order=wo))
    assert env["ok"] is True

    journal_path = tmp_path / ".architecture" / "ai" / "workorders.journal.jsonl"
    assert journal_path.exists()
    lines = [
        json.loads(l) for l in journal_path.read_text().splitlines() if l.strip()
    ]
    assert len(lines) == 1
    entry = lines[0]
    assert entry["event"] == "ai.workorder.submit"
    assert entry["payload"]["work_order_id"] == "wo-test-001"
    assert entry["payload"]["job_id"] == env["job_id"]
    assert entry["payload"]["requested_by"] == "user@example.com"
    assert "timestamp" in entry["payload"]


def test_non_dict_work_order(tmp_path: Path, submit) -> None:
    env = _run(submit(repo_path=str(tmp_path), work_order="not a dict"))
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_missing_repo_path(tmp_path: Path, submit) -> None:
    missing = tmp_path / "does-not-exist"
    env = _run(submit(repo_path=str(missing), work_order=_valid_wo()))
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


def test_missing_required_field(tmp_path: Path, submit) -> None:
    wo = _valid_wo()
    del wo["intent"]
    env = _run(submit(repo_path=str(tmp_path), work_order=wo))
    assert env["ok"] is False
    assert env["error"]["code"] == "SCHEMA_VIOLATION"
    assert env["error"]["details"]["errors"]


def test_empty_input_slice_refs(tmp_path: Path, submit) -> None:
    wo = _valid_wo()
    wo["input_slice_refs"] = []
    env = _run(submit(repo_path=str(tmp_path), work_order=wo))
    assert env["ok"] is False
    assert env["error"]["code"] == "SCHEMA_VIOLATION"
    assert env["error"]["details"]["errors"]


def test_bad_created_at(tmp_path: Path, submit) -> None:
    wo = _valid_wo()
    wo["created_at"] = "not-an-iso-date"
    env = _run(submit(repo_path=str(tmp_path), work_order=wo))
    assert env["ok"] is False
    assert env["error"]["code"] == "SCHEMA_VIOLATION"
    assert env["error"]["details"]["errors"]


def test_duplicate_submit(tmp_path: Path, submit) -> None:
    wo = _valid_wo()
    env1 = _run(submit(repo_path=str(tmp_path), work_order=wo))
    assert env1["ok"] is True
    env2 = _run(submit(repo_path=str(tmp_path), work_order=wo))
    assert env2["ok"] is False
    assert env2["error"]["code"] == "PRECONDITION_FAILED"
    assert env2["error"]["details"]["work_order_id"] == "wo-test-001"
    assert env2["error"]["details"]["reason"] == "already_exists"


def test_yaml_round_trip(tmp_path: Path, submit) -> None:
    from architecture_model.ai.work_order import WorkOrder

    wo = _valid_wo()
    env = _run(submit(repo_path=str(tmp_path), work_order=wo))
    assert env["ok"] is True
    yaml_path = tmp_path / ".architecture" / "ai" / "workorders" / "wo-test-001.yaml"
    data = yaml.safe_load(yaml_path.read_text())
    parsed = WorkOrder.from_dict(data)
    assert parsed.id == "wo-test-001"
    assert parsed.intent == wo["intent"]
    assert parsed.requested_by == wo["requested_by"]


def test_journal_appends_across_submits(tmp_path: Path, submit) -> None:
    env1 = _run(submit(repo_path=str(tmp_path), work_order=_valid_wo("wo-1")))
    env2 = _run(submit(repo_path=str(tmp_path), work_order=_valid_wo("wo-2")))
    assert env1["ok"] and env2["ok"]

    journal_path = tmp_path / ".architecture" / "ai" / "workorders.journal.jsonl"
    lines = [
        json.loads(l) for l in journal_path.read_text().splitlines() if l.strip()
    ]
    assert len(lines) == 2
    assert lines[0]["payload"]["work_order_id"] == "wo-1"
    assert lines[1]["payload"]["work_order_id"] == "wo-2"


def test_job_state_and_wo_id(tmp_path: Path, submit) -> None:
    from architecture_model.ai.jobs import JobStore, JobState

    env = _run(submit(repo_path=str(tmp_path), work_order=_valid_wo("wo-42")))
    assert env["ok"] is True
    store = JobStore(root=tmp_path)
    job = store.get(env["job_id"])
    assert job.state == JobState.draft
    assert job.work_order_id == "wo-42"


def test_deterministic_envelope_shape(tmp_path: Path, submit, tmp_path_factory) -> None:
    other = tmp_path_factory.mktemp("other")
    env1 = _run(submit(repo_path=str(tmp_path), work_order=_valid_wo("wo-a")))
    env2 = _run(submit(repo_path=str(other), work_order=_valid_wo("wo-b")))
    assert env1["ok"] and env2["ok"]
    assert set(env1) == set(env2) == {"ok", "work_order_id", "job_id"}
