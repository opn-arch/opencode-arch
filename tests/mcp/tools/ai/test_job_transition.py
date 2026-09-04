"""Tests for architect_job_transition MCP tool (T14)."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest


def _run(coro):
    return asyncio.run(coro)


def _valid_wo(wo_id: str = "wo-tr-001") -> dict:
    return {
        "id": wo_id,
        "intent": "Test job transitions",
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
def transition_tool():
    from opencode_arch.mcp.tools.ai.job_transition import (
        architect_job_transition_tool,
    )
    return architect_job_transition_tool


def _submit(submit, repo: Path, wo_id: str = "wo-tr-001") -> str:
    env = _run(submit(repo_path=str(repo), work_order=_valid_wo(wo_id)))
    assert env["ok"], env
    return env["job_id"]


def _tr(transition_tool, repo: Path, job_id: str, new_state: str, **kw) -> dict:
    return _run(
        transition_tool(
            repo_path=str(repo), job_id=job_id, new_state=new_state, **kw
        )
    )


def test_happy_draft_to_approved(
    tmp_path: Path, submit, transition_tool
) -> None:
    job_id = _submit(submit, tmp_path)
    env = _tr(transition_tool, tmp_path, job_id, "approved")
    assert env["ok"] is True, env
    assert env["job"]["state"] == "approved"


def test_chain_to_validating(tmp_path: Path, submit, transition_tool) -> None:
    job_id = _submit(submit, tmp_path)
    for state in ("approved", "queued", "running", "validating"):
        env = _tr(transition_tool, tmp_path, job_id, state)
        assert env["ok"] is True, (state, env)
        assert env["job"]["state"] == state


def test_terminal_completed_with_result_ref(
    tmp_path: Path, submit, transition_tool
) -> None:
    job_id = _submit(submit, tmp_path)
    for state in ("approved", "queued", "running", "validating"):
        _tr(transition_tool, tmp_path, job_id, state)
    env = _tr(
        transition_tool,
        tmp_path,
        job_id,
        "completed",
        result_ref="path/to/proposal.yaml",
    )
    assert env["ok"] is True, env
    assert env["job"]["state"] == "completed"
    assert env["job"]["result_ref"] == "path/to/proposal.yaml"


def test_terminal_completed_missing_result_ref(
    tmp_path: Path, submit, transition_tool
) -> None:
    job_id = _submit(submit, tmp_path)
    for state in ("approved", "queued", "running", "validating"):
        _tr(transition_tool, tmp_path, job_id, state)
    env = _tr(transition_tool, tmp_path, job_id, "completed")
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"
    assert "result_ref" in env["error"]["details"]["reason"]


def test_terminal_failed_with_error(
    tmp_path: Path, submit, transition_tool
) -> None:
    job_id = _submit(submit, tmp_path)
    for state in ("approved", "queued", "running"):
        _tr(transition_tool, tmp_path, job_id, state)
    env = _tr(transition_tool, tmp_path, job_id, "failed", error="oops")
    assert env["ok"] is True, env
    assert env["job"]["state"] == "failed"
    assert env["job"]["error"] == "oops"


def test_terminal_failed_missing_error(
    tmp_path: Path, submit, transition_tool
) -> None:
    job_id = _submit(submit, tmp_path)
    for state in ("approved", "queued", "running"):
        _tr(transition_tool, tmp_path, job_id, state)
    env = _tr(transition_tool, tmp_path, job_id, "failed")
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"
    assert "error" in env["error"]["details"]["reason"]


def test_invalid_transition_draft_to_completed(
    tmp_path: Path, submit, transition_tool
) -> None:
    job_id = _submit(submit, tmp_path)
    env = _tr(
        transition_tool,
        tmp_path,
        job_id,
        "completed",
        result_ref="p.yaml",
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "PRECONDITION_FAILED"
    details = env["error"]["details"]
    assert details["from_state"] == "draft"
    assert details["to_state"] == "completed"
    assert isinstance(details["allowed"], list)
    assert details["allowed"] == sorted(details["allowed"])
    assert "approved" in details["allowed"]


def test_unknown_new_state(tmp_path: Path, submit, transition_tool) -> None:
    job_id = _submit(submit, tmp_path)
    env = _tr(transition_tool, tmp_path, job_id, "pizza")
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"
    details = env["error"]["details"]
    assert details["new_state"] == "pizza"
    assert "draft" in details["valid_states"]
    assert "completed" in details["valid_states"]


def test_missing_job(tmp_path: Path, transition_tool) -> None:
    env = _tr(transition_tool, tmp_path, "job-nope", "approved")
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"]["reason"] == "job_missing"


def test_missing_repo(tmp_path: Path, transition_tool) -> None:
    missing = tmp_path / "nope"
    env = _tr(transition_tool, missing, "job-x", "approved")
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"]["reason"] == "repo_missing"


def test_empty_job_id(tmp_path: Path, transition_tool) -> None:
    env = _tr(transition_tool, tmp_path, "", "approved")
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_actor_defaults_to_system(
    tmp_path: Path, submit, transition_tool
) -> None:
    job_id = _submit(submit, tmp_path)
    env = _tr(transition_tool, tmp_path, job_id, "approved", actor=None)
    assert env["ok"] is True
    assert env["job"]["history"][-1]["actor"] == "system"


def test_reason_preserved_in_history(
    tmp_path: Path, submit, transition_tool
) -> None:
    job_id = _submit(submit, tmp_path)
    env = _tr(
        transition_tool, tmp_path, job_id, "approved", reason="looks good"
    )
    assert env["ok"] is True
    assert env["job"]["history"][-1]["reason"] == "looks good"


def test_history_ordered(tmp_path: Path, submit, transition_tool) -> None:
    job_id = _submit(submit, tmp_path)
    for state in ("approved", "queued", "running", "validating"):
        _tr(transition_tool, tmp_path, job_id, state)
    env = _tr(
        transition_tool,
        tmp_path,
        job_id,
        "completed",
        result_ref="p.yaml",
    )
    assert env["ok"] is True
    history = env["job"]["history"]
    to_states = [e["to_state"] for e in history]
    assert to_states == [
        "draft",
        "approved",
        "queued",
        "running",
        "validating",
        "completed",
    ]
