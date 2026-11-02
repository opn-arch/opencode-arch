"""Tests for the ``arch_learn`` materialize MCP tool.

``arch_learn`` closes the learning loop's first join: it mines lessons
exactly as ``arch_lessons`` does, picks the highest-ranked lesson (or a
caller-targeted one via ``subject`` / ``lesson_type``), builds a
``WorkOrder`` via ``lesson_to_work_order``, persists it, and creates a
Job that STOPS at ``draft`` — the review gate. Nothing is applied or
published; the draft job is routed through the existing
``proposal_validate → proposal_apply`` pipeline downstream.
"""
from __future__ import annotations

import asyncio

import yaml

from opencode_arch.mcp.tools.arch_learn import arch_learn


def _run(coro):
    return asyncio.run(coro)


def test_arch_learn_materializes_draft_workorder(tmp_path, _seed_model_with_signals):
    _seed_model_with_signals(tmp_path)
    env = _run(arch_learn(repo_path=str(tmp_path)))
    assert env["ok"] is True
    assert env["job_state"] == "draft"
    assert env["work_order_id"] and env["job_id"]
    assert isinstance(env["intent"], str) and env["intent"]


def test_arch_learn_persists_workorder_file_and_draft_job(
    tmp_path, _seed_model_with_signals
):
    _seed_model_with_signals(tmp_path)
    env = _run(arch_learn(repo_path=str(tmp_path)))
    assert env["ok"] is True

    wo_path = (
        tmp_path
        / ".architecture"
        / "ai"
        / "workorders"
        / f"{env['work_order_id']}.yaml"
    )
    assert wo_path.exists()
    wo = yaml.safe_load(wo_path.read_text())
    assert wo["id"] == env["work_order_id"]

    # The Job stops at draft — the gate. Nothing queued / applied.
    from openag.ai.jobs import JobStore

    job = JobStore(root=tmp_path).get(env["job_id"])
    assert job.state.value == "draft"
    # Draft is the terminal state of this tool: the job has only its
    # creation event in history (no approve/queue transitions).
    assert len(job.history) == 1


def test_arch_learn_targets_specific_lesson(tmp_path, _seed_model_with_signals):
    _seed_model_with_signals(tmp_path)
    env = _run(
        arch_learn(repo_path=str(tmp_path), lesson_type="lesson:recurring-gap")
    )
    assert env["ok"] is True
    assert env["job_state"] == "draft"
    assert "lesson:recurring-gap" in env["intent"]


def test_arch_learn_no_matching_lesson_returns_not_found(
    tmp_path, _seed_model_with_signals
):
    _seed_model_with_signals(tmp_path)
    env = _run(
        arch_learn(repo_path=str(tmp_path), lesson_type="lesson:does-not-exist")
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"]["reason"] == "no_lessons"


def test_arch_learn_no_lessons_returns_not_found(tmp_path):
    # Repo exists with a model that yields no mineable signals.
    model_dir = tmp_path / ".architecture" / "model"
    model_dir.mkdir(parents=True)
    (model_dir / "empty.v3.yaml").write_text("entities: []\nrelationships: []\n")
    env = _run(arch_learn(repo_path=str(tmp_path)))
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"]["reason"] == "no_lessons"


def test_arch_learn_missing_repo_returns_not_found():
    env = _run(arch_learn(repo_path="/nonexistent/repo/path"))
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
