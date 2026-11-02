"""Tests for the ``arch_learn`` materialize MCP tool.

``arch_learn`` closes the learning loop's first join: it mines lessons
exactly as ``arch_lessons`` does, picks the highest-ranked lesson (or a
caller-targeted one via ``subject`` / ``lesson_type``), builds a
``WorkOrder`` via ``lesson_to_work_order``, persists it, and creates a
Job that STOPS at ``draft`` — the review gate. Nothing is applied or
published; the draft job is routed through the existing
``proposal_validate → proposal_apply`` pipeline downstream.

No extra signal seeding is needed: the insulin-pump exemplar seeded by
``_seed_model`` carries owed-promise gaps, so the always-error
``lesson:recurring-gap`` miner fires on the seeded model alone (no
generation history required).
"""
from __future__ import annotations

import asyncio

import yaml

from opencode_arch.mcp.tools.arch_learn import arch_learn
from opencode_arch.mcp.tools.arch_lessons import arch_lessons


def _run(coro):
    return asyncio.run(coro)


def _top_lesson(repo_path: str) -> dict:
    """Mine lessons via arch_lessons and return the top ranked record."""
    out = _run(arch_lessons(repo_path=repo_path))
    assert out["ok"] is True
    lessons = out["digest"]["lessons"]
    assert lessons, "exemplar should mine >= 1 lesson"
    return lessons[0]


def test_arch_learn_materializes_draft_workorder(tmp_path, _seed_model):
    _seed_model(tmp_path)
    env = _run(arch_learn(repo_path=str(tmp_path)))
    assert env["ok"] is True
    assert env["job_state"] == "draft"
    assert env["work_order_id"] and env["job_id"]
    assert isinstance(env["intent"], str) and env["intent"]


def test_arch_learn_persists_workorder_file_and_draft_job(tmp_path, _seed_model):
    _seed_model(tmp_path)
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


def test_arch_learn_targets_specific_lesson_type(tmp_path, _seed_model):
    _seed_model(tmp_path)
    env = _run(
        arch_learn(repo_path=str(tmp_path), lesson_type="lesson:recurring-gap")
    )
    assert env["ok"] is True
    assert env["job_state"] == "draft"
    assert "lesson:recurring-gap" in env["intent"]


def test_arch_learn_targets_specific_subject(tmp_path, _seed_model):
    _seed_model(tmp_path)
    # Discover a real mined subject, then target it via the subject filter.
    top = _top_lesson(str(tmp_path))
    subject = top["subject"]

    env = _run(arch_learn(repo_path=str(tmp_path), subject=subject))
    assert env["ok"] is True
    assert env["job_state"] == "draft"

    # The materialized WorkOrder must correspond to the targeted subject:
    # lesson_to_work_order pins it in parameters["subject"].
    wo_path = (
        tmp_path
        / ".architecture"
        / "ai"
        / "workorders"
        / f"{env['work_order_id']}.yaml"
    )
    wo = yaml.safe_load(wo_path.read_text())
    assert wo["parameters"]["subject"] == subject


def test_arch_learn_targets_subject_and_lesson_type(tmp_path, _seed_model):
    _seed_model(tmp_path)
    # Discover a real (subject, lesson_type) pair and target both filters.
    top = _top_lesson(str(tmp_path))
    subject = top["subject"]
    lesson_type = top["lesson_type"]

    env = _run(
        arch_learn(
            repo_path=str(tmp_path), subject=subject, lesson_type=lesson_type
        )
    )
    assert env["ok"] is True
    assert env["job_state"] == "draft"

    wo_path = (
        tmp_path
        / ".architecture"
        / "ai"
        / "workorders"
        / f"{env['work_order_id']}.yaml"
    )
    wo = yaml.safe_load(wo_path.read_text())
    assert wo["parameters"]["subject"] == subject
    assert wo["parameters"]["lesson_type"] == lesson_type


def test_arch_learn_no_matching_lesson_returns_not_found(tmp_path, _seed_model):
    _seed_model(tmp_path)
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
