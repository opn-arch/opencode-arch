"""Tests for the T16 ``architect_job_run`` MCP tool."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

# Make the sibling ``_proposer_fixtures.py`` importable as a top-level
# module name so it can be referenced from a plugin dotted path
# (``_proposer_fixtures:stub_valid_proposal``).
_FIXTURE_DIR = Path(__file__).parent
if str(_FIXTURE_DIR) not in sys.path:
    sys.path.insert(0, str(_FIXTURE_DIR))


# ---------------------------------------------------------------------------
# Setup helpers (mirrors the T15 worker test fixture patterns)
# ---------------------------------------------------------------------------


def _valid_wo_dict(wo_id: str = "wo-1") -> dict:
    return {
        "id": wo_id,
        "intent": "test intent",
        "input_slice_refs": [
            {"slice_id": "slice-1", "model_revision": "rev-1"}
        ],
        "expected_proposal_kinds": ["model-patch"],
        "budget": {"max_tokens": 1000, "max_wall_seconds": 60},
        "requested_by": "tester",
        "created_at": "2026-09-04T00:00:00+00:00",
    }


def _persist_wo(repo: Path, wo_dict: dict) -> None:
    from architecture_model.ai.work_order import WorkOrder
    from architecture_model.lifecycle.atomic_store import write_atomic

    wo = WorkOrder.from_dict(wo_dict)
    wo_dir = repo / ".architecture" / "ai" / "workorders"
    wo_dir.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(
        wo.to_dict(), sort_keys=True, default_flow_style=False
    )
    write_atomic(wo_dir / f"{wo.id}.yaml", text.encode("utf-8"))


def _make_queued_job(repo: Path, wo_id: str = "wo-1") -> str:
    from architecture_model.ai.jobs import JobState, JobStore

    _persist_wo(repo, _valid_wo_dict(wo_id))
    store = JobStore(root=repo)
    job = store.create(work_order_id=wo_id)
    store.transition(job.id, JobState.approved, actor="tester")
    store.transition(job.id, JobState.queued, actor="tester")
    return job.id


def _make_draft_job(repo: Path, wo_id: str = "wo-1") -> str:
    from architecture_model.ai.jobs import JobStore

    _persist_wo(repo, _valid_wo_dict(wo_id))
    store = JobStore(root=repo)
    job = store.create(work_order_id=wo_id)
    return job.id


def _write_config(repo: Path, config: dict | str | None) -> None:
    cfg_dir = repo / ".architecture" / "ai"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "proposer_config.yaml"
    if config is None:
        return
    if isinstance(config, str):
        cfg_path.write_text(config, encoding="utf-8")
    else:
        cfg_path.write_text(
            yaml.safe_dump(config, sort_keys=True, default_flow_style=False),
            encoding="utf-8",
        )


VALID_PLUGIN = "_proposer_fixtures:stub_valid_proposal"
RAISING_PLUGIN = "_proposer_fixtures:stub_raising"
NON_PROPOSAL_PLUGIN = "_proposer_fixtures:stub_non_proposal"
INVALID_PROP_PLUGIN = "_proposer_fixtures:stub_invalid_proposal"
NON_CALLABLE_PLUGIN = "_proposer_fixtures:NOT_A_FUNCTION"


async def _call(repo: Path, job_id: str) -> dict:
    from opencode_arch.mcp.tools.ai.job_run import architect_job_run_tool

    return await architect_job_run_tool(str(repo), job_id)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_happy_path_completes(tmp_path: Path) -> None:
    job_id = _make_queued_job(tmp_path, "wo-1")
    _write_config(tmp_path, {"plugin": VALID_PLUGIN})

    result = await _call(tmp_path, job_id)

    assert result["ok"] is True, result
    assert result["job"]["state"] == "completed"
    assert result["proposal_ref"] == f".architecture/ai/proposals/{job_id}.yaml"
    assert (tmp_path / result["proposal_ref"]).exists()


async def test_happy_path_enabled_true_explicit(tmp_path: Path) -> None:
    job_id = _make_queued_job(tmp_path, "wo-1")
    _write_config(tmp_path, {"plugin": VALID_PLUGIN, "enabled": True})

    result = await _call(tmp_path, job_id)
    assert result["ok"] is True
    assert result["job"]["state"] == "completed"


# ---------------------------------------------------------------------------
# Config errors
# ---------------------------------------------------------------------------


async def test_config_missing(tmp_path: Path) -> None:
    job_id = _make_queued_job(tmp_path, "wo-1")

    result = await _call(tmp_path, job_id)
    assert result["ok"] is False
    assert result["error"]["code"] == "PRECONDITION_FAILED"
    assert result["error"]["details"]["reason"] == "no_proposer_configured"
    assert (
        result["error"]["details"]["expected_path"]
        == ".architecture/ai/proposer_config.yaml"
    )


async def test_config_disabled(tmp_path: Path) -> None:
    job_id = _make_queued_job(tmp_path, "wo-1")
    _write_config(tmp_path, {"plugin": VALID_PLUGIN, "enabled": False})

    result = await _call(tmp_path, job_id)
    assert result["error"]["code"] == "PRECONDITION_FAILED"
    assert result["error"]["details"]["reason"] == "proposer_disabled"


async def test_config_not_a_dict(tmp_path: Path) -> None:
    job_id = _make_queued_job(tmp_path, "wo-1")
    _write_config(tmp_path, "just a scalar string\n")

    result = await _call(tmp_path, job_id)
    assert result["error"]["code"] == "PRECONDITION_FAILED"
    assert result["error"]["details"]["reason"] == "proposer_config_malformed"


async def test_config_missing_plugin_key(tmp_path: Path) -> None:
    job_id = _make_queued_job(tmp_path, "wo-1")
    _write_config(tmp_path, {"enabled": True})

    result = await _call(tmp_path, job_id)
    assert result["error"]["code"] == "PRECONDITION_FAILED"
    assert result["error"]["details"]["reason"] == "proposer_config_malformed"


async def test_config_plugin_not_a_string(tmp_path: Path) -> None:
    job_id = _make_queued_job(tmp_path, "wo-1")
    _write_config(tmp_path, {"plugin": 42})

    result = await _call(tmp_path, job_id)
    assert result["error"]["code"] == "PRECONDITION_FAILED"
    assert result["error"]["details"]["reason"] == "proposer_config_malformed"


# ---------------------------------------------------------------------------
# Plugin resolution errors
# ---------------------------------------------------------------------------


async def test_plugin_bad_format_no_colon(tmp_path: Path) -> None:
    job_id = _make_queued_job(tmp_path, "wo-1")
    _write_config(tmp_path, {"plugin": "no_colon_here"})

    result = await _call(tmp_path, job_id)
    assert result["error"]["code"] == "PRECONDITION_FAILED"
    assert result["error"]["details"]["reason"] == "proposer_config_malformed"


async def test_plugin_bad_format_empty_side(tmp_path: Path) -> None:
    job_id = _make_queued_job(tmp_path, "wo-1")
    _write_config(tmp_path, {"plugin": "somemod:"})

    result = await _call(tmp_path, job_id)
    assert result["error"]["code"] == "PRECONDITION_FAILED"
    assert result["error"]["details"]["reason"] == "proposer_config_malformed"


async def test_plugin_module_not_found(tmp_path: Path) -> None:
    job_id = _make_queued_job(tmp_path, "wo-1")
    _write_config(
        tmp_path, {"plugin": "no_such_module_xyz_123:some_fn"}
    )

    result = await _call(tmp_path, job_id)
    assert result["error"]["code"] == "PRECONDITION_FAILED"
    assert result["error"]["details"]["reason"] == "proposer_plugin_not_loadable"
    assert "detail" in result["error"]["details"]


async def test_plugin_function_not_found(tmp_path: Path) -> None:
    job_id = _make_queued_job(tmp_path, "wo-1")
    _write_config(
        tmp_path, {"plugin": "_proposer_fixtures:not_a_real_function"}
    )

    result = await _call(tmp_path, job_id)
    assert result["error"]["code"] == "PRECONDITION_FAILED"
    assert result["error"]["details"]["reason"] == "proposer_plugin_not_loadable"


async def test_plugin_not_callable(tmp_path: Path) -> None:
    job_id = _make_queued_job(tmp_path, "wo-1")
    _write_config(tmp_path, {"plugin": NON_CALLABLE_PLUGIN})

    result = await _call(tmp_path, job_id)
    assert result["error"]["code"] == "PRECONDITION_FAILED"
    assert result["error"]["details"]["reason"] == "proposer_plugin_not_callable"


# ---------------------------------------------------------------------------
# Job & work-order errors
# ---------------------------------------------------------------------------


async def test_job_missing(tmp_path: Path) -> None:
    _write_config(tmp_path, {"plugin": VALID_PLUGIN})

    result = await _call(tmp_path, "job-nope-nope")
    assert result["error"]["code"] == "NOT_FOUND"
    assert result["error"]["details"]["reason"] == "job_missing"


async def test_job_not_queued(tmp_path: Path) -> None:
    job_id = _make_draft_job(tmp_path, "wo-1")
    _write_config(tmp_path, {"plugin": VALID_PLUGIN})

    result = await _call(tmp_path, job_id)
    assert result["error"]["code"] == "PRECONDITION_FAILED"
    assert result["error"]["details"]["reason"] == "job_not_queued"
    assert result["error"]["details"]["state"] == "draft"


async def test_workorder_missing(tmp_path: Path) -> None:
    from architecture_model.ai.jobs import JobState, JobStore

    _write_config(tmp_path, {"plugin": VALID_PLUGIN})
    store = JobStore(root=tmp_path)
    job = store.create(work_order_id="wo-missing-yaml")
    store.transition(job.id, JobState.approved)
    store.transition(job.id, JobState.queued)

    result = await _call(tmp_path, job.id)
    assert result["error"]["code"] == "NOT_FOUND"
    assert result["error"]["details"]["reason"] == "workorder_missing"


# ---------------------------------------------------------------------------
# Proposer runtime failures — envelope still ok:True with failed job.
# ---------------------------------------------------------------------------


async def test_proposer_raises_reports_failed(tmp_path: Path) -> None:
    job_id = _make_queued_job(tmp_path, "wo-1")
    _write_config(tmp_path, {"plugin": RAISING_PLUGIN})

    result = await _call(tmp_path, job_id)
    assert result["ok"] is True
    assert result["job"]["state"] == "failed"
    assert result["proposal_ref"] is None
    assert "error" in result
    assert "proposer" in result["error"].lower() or "stub" in result["error"].lower()


async def test_proposer_returns_non_proposal_reports_failed(tmp_path: Path) -> None:
    job_id = _make_queued_job(tmp_path, "wo-1")
    _write_config(tmp_path, {"plugin": NON_PROPOSAL_PLUGIN})

    result = await _call(tmp_path, job_id)
    assert result["ok"] is True
    assert result["job"]["state"] == "failed"
    assert result["proposal_ref"] is None
    assert "non-Proposal" in result["error"] or "error" in result


async def test_proposer_returns_invalid_proposal_reports_failed(
    tmp_path: Path,
) -> None:
    job_id = _make_queued_job(tmp_path, "wo-1")
    _write_config(tmp_path, {"plugin": INVALID_PROP_PLUGIN})

    result = await _call(tmp_path, job_id)
    assert result["ok"] is True
    assert result["job"]["state"] == "failed"
    # Invalid proposal → proposal file WAS written before validation failed,
    # but the job did not complete → proposal_ref reported as None.
    assert result["proposal_ref"] is None
    assert "validation" in result["error"].lower()


# ---------------------------------------------------------------------------
# Argument validation & determinism
# ---------------------------------------------------------------------------


async def test_missing_repo_path(tmp_path: Path) -> None:
    from opencode_arch.mcp.tools.ai.job_run import architect_job_run_tool

    result = await architect_job_run_tool(
        str(tmp_path / "does_not_exist"), "job-x"
    )
    assert result["error"]["code"] == "NOT_FOUND"


async def test_empty_job_id(tmp_path: Path) -> None:
    _write_config(tmp_path, {"plugin": VALID_PLUGIN})
    result = await _call(tmp_path, "")
    assert result["error"]["code"] == "INVALID_ARGUMENT"


async def test_determinism_identical_setup(tmp_path, tmp_path_factory) -> None:
    repo_a = tmp_path
    repo_b = tmp_path_factory.mktemp("repo_b")

    job_a = _make_queued_job(repo_a, "wo-1")
    job_b = _make_queued_job(repo_b, "wo-1")
    _write_config(repo_a, {"plugin": VALID_PLUGIN})
    _write_config(repo_b, {"plugin": VALID_PLUGIN})

    ra = await _call(repo_a, job_a)
    rb = await _call(repo_b, job_b)

    # The proposal bytes are deterministic (T15 proved this).
    a_bytes = (repo_a / ra["proposal_ref"]).read_bytes()
    b_bytes = (repo_b / rb["proposal_ref"]).read_bytes()
    assert a_bytes == b_bytes
    assert ra["ok"] is True and rb["ok"] is True
    assert ra["job"]["state"] == rb["job"]["state"] == "completed"
