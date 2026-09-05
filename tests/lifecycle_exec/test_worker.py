"""Tests for the AI job worker executor (T15)."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

import pytest
import yaml


# ---------------------------------------------------------------------------
# Helpers
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
    text = yaml.safe_dump(wo.to_dict(), sort_keys=True, default_flow_style=False)
    write_atomic(wo_dir / f"{wo.id}.yaml", text.encode("utf-8"))


def _make_queued_job(repo: Path, wo_id: str = "wo-1") -> str:
    """Create WO on disk, create Job, transition draft→approved→queued."""
    from architecture_model.ai.jobs import JobStore, JobState

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


def _make_proposer(wo_id: str = "wo-1") -> Callable:
    """Return a proposer that yields a minimal-valid ModelPatch."""
    from architecture_model.ai.proposals import ModelPatch, Provenance

    def proposer(_wo):
        return ModelPatch(
            provenance=Provenance(
                work_order_id=wo_id,
                model_version="rev-1",
                prompt_digest="digest-1",
            ),
            operations=[],
        )

    return proposer


# ---------------------------------------------------------------------------
# dequeue_next
# ---------------------------------------------------------------------------


def test_dequeue_next_empty_repo_returns_none(tmp_path: Path) -> None:
    from opencode_arch.lifecycle_exec.worker import dequeue_next

    assert dequeue_next(str(tmp_path)) is None


def test_dequeue_next_returns_queued_job(tmp_path: Path) -> None:
    from opencode_arch.lifecycle_exec.worker import dequeue_next

    job_id = _make_queued_job(tmp_path, "wo-a")
    result = dequeue_next(str(tmp_path))
    assert result is not None
    assert result.id == job_id


def test_dequeue_next_earliest_created_at_wins(tmp_path: Path) -> None:
    from architecture_model.ai.jobs import JobState, JobStore
    from opencode_arch.lifecycle_exec.worker import dequeue_next

    # Older job
    _persist_wo(tmp_path, _valid_wo_dict("wo-a"))
    _persist_wo(tmp_path, _valid_wo_dict("wo-b"))
    store = JobStore(root=tmp_path)
    j1 = store.create(work_order_id="wo-a")
    time.sleep(0.01)
    j2 = store.create(work_order_id="wo-b")
    for j in (j1, j2):
        store.transition(j.id, JobState.approved)
        store.transition(j.id, JobState.queued)

    result = dequeue_next(str(tmp_path))
    assert result is not None
    assert result.id == j1.id
    assert result.created_at <= j2.created_at


def test_dequeue_next_ignores_non_queued(tmp_path: Path) -> None:
    from architecture_model.ai.jobs import JobState, JobStore
    from opencode_arch.lifecycle_exec.worker import dequeue_next

    # draft
    _persist_wo(tmp_path, _valid_wo_dict("wo-draft"))
    # approved
    _persist_wo(tmp_path, _valid_wo_dict("wo-approved"))
    # queued (the one we want)
    _persist_wo(tmp_path, _valid_wo_dict("wo-queued"))
    # running
    _persist_wo(tmp_path, _valid_wo_dict("wo-running"))

    store = JobStore(root=tmp_path)
    j_draft = store.create(work_order_id="wo-draft")
    j_approved = store.create(work_order_id="wo-approved")
    j_queued = store.create(work_order_id="wo-queued")
    j_running = store.create(work_order_id="wo-running")

    store.transition(j_approved.id, JobState.approved)
    store.transition(j_queued.id, JobState.approved)
    store.transition(j_queued.id, JobState.queued)
    store.transition(j_running.id, JobState.approved)
    store.transition(j_running.id, JobState.queued)
    store.transition(j_running.id, JobState.running)

    result = dequeue_next(str(tmp_path))
    assert result is not None
    assert result.id == j_queued.id


def test_dequeue_next_nonexistent_repo_raises(tmp_path: Path) -> None:
    from opencode_arch.lifecycle_exec.worker import dequeue_next

    missing = tmp_path / "nope"
    with pytest.raises(ValueError):
        dequeue_next(str(missing))


# ---------------------------------------------------------------------------
# run_job — happy path & basic errors
# ---------------------------------------------------------------------------


def test_run_job_happy_path_completes(tmp_path: Path) -> None:
    from architecture_model.ai.jobs import JobState
    from opencode_arch.lifecycle_exec.worker import run_job

    job_id = _make_queued_job(tmp_path, "wo-1")
    proposer = _make_proposer("wo-1")

    job = run_job(str(tmp_path), job_id, proposer=proposer)
    assert job.state == JobState.completed
    assert job.result_ref is not None
    # posix-relative
    assert not job.result_ref.startswith("/")
    assert "\\" not in job.result_ref
    # proposal file exists
    proposal_path = tmp_path / job.result_ref
    assert proposal_path.exists()


def test_run_job_result_ref_is_posix_relative(tmp_path: Path) -> None:
    from opencode_arch.lifecycle_exec.worker import run_job

    job_id = _make_queued_job(tmp_path, "wo-1")
    job = run_job(str(tmp_path), job_id, proposer=_make_proposer("wo-1"))
    assert job.result_ref == f".architecture/ai/proposals/{job_id}.yaml"


def test_run_job_proposer_raises_marks_failed(tmp_path: Path) -> None:
    from architecture_model.ai.jobs import JobState
    from opencode_arch.lifecycle_exec.worker import run_job

    job_id = _make_queued_job(tmp_path, "wo-1")

    def bad_proposer(_wo):
        raise RuntimeError("boom")

    job = run_job(str(tmp_path), job_id, proposer=bad_proposer)
    assert job.state == JobState.failed
    assert "proposer error" in (job.error or "")
    assert "boom" in (job.error or "")


def test_run_job_non_proposal_return_marks_failed(tmp_path: Path) -> None:
    from architecture_model.ai.jobs import JobState
    from opencode_arch.lifecycle_exec.worker import run_job

    job_id = _make_queued_job(tmp_path, "wo-1")

    def bad_proposer(_wo):
        return {"not": "a proposal"}

    job = run_job(str(tmp_path), job_id, proposer=bad_proposer)
    assert job.state == JobState.failed
    assert "non-Proposal" in (job.error or "")


def test_run_job_none_return_marks_failed(tmp_path: Path) -> None:
    from architecture_model.ai.jobs import JobState
    from opencode_arch.lifecycle_exec.worker import run_job

    job_id = _make_queued_job(tmp_path, "wo-1")

    def bad_proposer(_wo):
        return None

    job = run_job(str(tmp_path), job_id, proposer=bad_proposer)
    assert job.state == JobState.failed
    assert "non-Proposal" in (job.error or "")


def test_run_job_not_queued_raises(tmp_path: Path) -> None:
    from opencode_arch.lifecycle_exec.worker import run_job

    job_id = _make_draft_job(tmp_path, "wo-1")
    with pytest.raises(ValueError, match="not queued"):
        run_job(str(tmp_path), job_id, proposer=_make_proposer("wo-1"))


def test_run_job_missing_workorder_yaml_raises(tmp_path: Path) -> None:
    from architecture_model.ai.jobs import JobState, JobStore
    from opencode_arch.lifecycle_exec.worker import run_job

    # Manually create a queued job without persisting the WO YAML.
    store = JobStore(root=tmp_path)
    job = store.create(work_order_id="wo-missing")
    store.transition(job.id, JobState.approved)
    store.transition(job.id, JobState.queued)

    with pytest.raises(FileNotFoundError):
        run_job(str(tmp_path), job.id, proposer=_make_proposer("wo-missing"))


def test_run_job_unknown_job_id_raises_keyerror(tmp_path: Path) -> None:
    from opencode_arch.lifecycle_exec.worker import run_job

    with pytest.raises(KeyError):
        run_job(str(tmp_path), "job-does-not-exist", proposer=_make_proposer())


# ---------------------------------------------------------------------------
# validation failure
# ---------------------------------------------------------------------------


def test_run_job_validation_failure_marks_failed(tmp_path: Path) -> None:
    """Provenance work_order_id mismatch → validation error → failed."""
    from architecture_model.ai.jobs import JobState
    from architecture_model.ai.proposals import ModelPatch, Provenance
    from opencode_arch.lifecycle_exec.worker import run_job

    job_id = _make_queued_job(tmp_path, "wo-1")

    def proposer(_wo):
        # Mismatched work_order_id → provenance-mismatch error.
        return ModelPatch(
            provenance=Provenance(
                work_order_id="wo-WRONG",
                model_version="rev-1",
                prompt_digest="d",
            ),
            operations=[],
        )

    job = run_job(str(tmp_path), job_id, proposer=proposer)
    assert job.state == JobState.failed
    assert "validation failed" in (job.error or "")


# ---------------------------------------------------------------------------
# history / return-value semantics
# ---------------------------------------------------------------------------


def test_run_job_history_ordering_success(tmp_path: Path) -> None:
    from architecture_model.ai.jobs import JobState
    from opencode_arch.lifecycle_exec.worker import run_job

    job_id = _make_queued_job(tmp_path, "wo-1")
    job = run_job(str(tmp_path), job_id, proposer=_make_proposer("wo-1"))

    transitions = [(e.from_state, e.to_state) for e in job.history]
    # Should contain queued→running, running→validating, validating→completed
    assert (JobState.queued, JobState.running) in transitions
    assert (JobState.running, JobState.validating) in transitions
    assert (JobState.validating, JobState.completed) in transitions
    # Order preserved.
    idx_qr = transitions.index((JobState.queued, JobState.running))
    idx_rv = transitions.index((JobState.running, JobState.validating))
    idx_vc = transitions.index((JobState.validating, JobState.completed))
    assert idx_qr < idx_rv < idx_vc


def test_run_job_history_ordering_validation_failure(tmp_path: Path) -> None:
    from architecture_model.ai.jobs import JobState
    from architecture_model.ai.proposals import ModelPatch, Provenance
    from opencode_arch.lifecycle_exec.worker import run_job

    job_id = _make_queued_job(tmp_path, "wo-1")

    def proposer(_wo):
        return ModelPatch(
            provenance=Provenance(
                work_order_id="wo-WRONG",
                model_version="rev-1",
                prompt_digest="d",
            ),
            operations=[],
        )

    job = run_job(str(tmp_path), job_id, proposer=proposer)
    transitions = [(e.from_state, e.to_state) for e in job.history]
    assert (JobState.queued, JobState.running) in transitions
    assert (JobState.running, JobState.validating) in transitions
    assert (JobState.validating, JobState.failed) in transitions


def test_run_job_returns_final_job(tmp_path: Path) -> None:
    from architecture_model.ai.jobs import JobState, JobStore
    from opencode_arch.lifecycle_exec.worker import run_job

    job_id = _make_queued_job(tmp_path, "wo-1")
    returned = run_job(str(tmp_path), job_id, proposer=_make_proposer("wo-1"))

    persisted = JobStore(root=tmp_path).get(job_id)
    assert returned.state == persisted.state == JobState.completed
    assert returned.updated_at == persisted.updated_at
    assert returned.result_ref == persisted.result_ref


# ---------------------------------------------------------------------------
# proposal file round-trip & determinism
# ---------------------------------------------------------------------------


def test_run_job_proposal_yaml_roundtrip(tmp_path: Path) -> None:
    from architecture_model.ai.proposals import ModelPatch, proposal_from_dict
    from opencode_arch.lifecycle_exec.worker import run_job

    job_id = _make_queued_job(tmp_path, "wo-1")
    proposer = _make_proposer("wo-1")
    original = proposer(None)

    job = run_job(str(tmp_path), job_id, proposer=proposer)
    proposal_path = tmp_path / job.result_ref
    data = yaml.safe_load(proposal_path.read_text(encoding="utf-8"))
    parsed = proposal_from_dict(data)
    assert isinstance(parsed, ModelPatch)
    assert parsed.to_dict() == original.to_dict()


def test_run_job_deterministic_yaml_bytes(tmp_path: Path, tmp_path_factory) -> None:
    from opencode_arch.lifecycle_exec.worker import run_job

    repo_a = tmp_path
    repo_b = tmp_path_factory.mktemp("repo_b")

    # Same WO id in both repos → same proposal contents.
    job_a = _make_queued_job(repo_a, "wo-same")
    job_b = _make_queued_job(repo_b, "wo-same")

    proposer = _make_proposer("wo-same")
    ra = run_job(str(repo_a), job_a, proposer=proposer)
    rb = run_job(str(repo_b), job_b, proposer=proposer)

    bytes_a = (repo_a / ra.result_ref).read_bytes()
    bytes_b = (repo_b / rb.result_ref).read_bytes()
    assert bytes_a == bytes_b


def test_run_job_default_input_slices_empty(tmp_path: Path) -> None:
    """When input_slices is None, validator gets {} and drift check is skipped."""
    from architecture_model.ai.jobs import JobState
    from opencode_arch.lifecycle_exec.worker import run_job

    job_id = _make_queued_job(tmp_path, "wo-1")
    # No input_slices kwarg passed.
    job = run_job(str(tmp_path), job_id, proposer=_make_proposer("wo-1"))
    assert job.state == JobState.completed
