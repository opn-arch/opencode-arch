"""Tests for architect_job_get MCP tool (T14)."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest


def _run(coro):
    return asyncio.run(coro)


def _valid_wo(wo_id: str = "wo-get-001") -> dict:
    return {
        "id": wo_id,
        "intent": "Test job get",
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


@pytest.fixture
def get_tool():
    from opencode_arch.mcp.tools.ai.job_get import architect_job_get_tool
    return architect_job_get_tool


@pytest.fixture
def transition_tool():
    from opencode_arch.mcp.tools.ai.job_transition import (
        architect_job_transition_tool,
    )
    return architect_job_transition_tool


def _submit(submit, repo: Path, wo_id: str = "wo-get-001") -> str:
    env = _run(submit(repo_path=str(repo), work_order=_valid_wo(wo_id)))
    assert env["ok"], env
    return env["job_id"]


def test_happy_path(tmp_path: Path, submit, get_tool) -> None:
    job_id = _submit(submit, tmp_path)
    env = _run(get_tool(repo_path=str(tmp_path), job_id=job_id))
    assert env["ok"] is True, env
    job = env["job"]
    assert job["id"] == job_id
    assert job["state"] == "draft"
    assert job["work_order_id"] == "wo-get-001"
    assert isinstance(job["history"], list)
    assert job["history"][0]["to_state"] == "draft"


def test_empty_job_id(tmp_path: Path, get_tool) -> None:
    env = _run(get_tool(repo_path=str(tmp_path), job_id=""))
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_non_string_job_id(tmp_path: Path, get_tool) -> None:
    env = _run(get_tool(repo_path=str(tmp_path), job_id=123))  # type: ignore[arg-type]
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_job_missing(tmp_path: Path, get_tool) -> None:
    env = _run(get_tool(repo_path=str(tmp_path), job_id="job-does-not-exist"))
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"]["reason"] == "job_missing"


def test_repo_missing(tmp_path: Path, get_tool) -> None:
    missing = tmp_path / "nope"
    env = _run(get_tool(repo_path=str(missing), job_id="job-x"))
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"]["reason"] == "repo_missing"


def test_round_trip_get_transition_get(
    tmp_path: Path, submit, get_tool, transition_tool
) -> None:
    job_id = _submit(submit, tmp_path)
    env1 = _run(get_tool(repo_path=str(tmp_path), job_id=job_id))
    assert env1["job"]["state"] == "draft"

    env_t = _run(
        transition_tool(
            repo_path=str(tmp_path),
            job_id=job_id,
            new_state="approved",
            reason="ready",
        )
    )
    assert env_t["ok"] is True, env_t
    assert env_t["job"]["state"] == "approved"

    env2 = _run(get_tool(repo_path=str(tmp_path), job_id=job_id))
    assert env2["ok"] is True
    assert env2["job"]["state"] == "approved"
    assert env2["job"]["history"][-1]["to_state"] == "approved"
    assert env2["job"]["history"][-1]["reason"] == "ready"


def test_envelope_shape(tmp_path: Path, submit, get_tool) -> None:
    job_id = _submit(submit, tmp_path, "wo-shape-1")
    env = _run(get_tool(repo_path=str(tmp_path), job_id=job_id))
    assert set(env) == {"ok", "job"}
