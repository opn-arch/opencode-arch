"""Tests for the arch_lessons B-ROUND proprioception read MCP tool.

``arch_lessons`` is the thin OCA read-surface over the openAG kernel
``openag.kernel.lessons`` miner. It assembles the four proprioception signal
streams (history, observations, gaps, flags), derives + persists lessons, and
returns the ranked digest plus reviewable proposal stubs:
``{"digest": {"lessons": [...], "proposals": [...]}, "proposals": [...]}``.

It EMITS proposal stubs only — it never mutates the model nor submits a
workorder itself (those flow through the existing
``architect_workorder_submit → proposal_validate → proposal_apply`` pipeline).

NOTE: the tool self-instruments (wrapped in ``observe_tool_call``), so each
invocation appends its own ``oca:arch_lessons`` ``tool_call`` record to the
journal. Tests therefore use membership/subset assertions against the journal,
never exact-equality on the full observation list.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest

from opencode_arch.mcp.tools.arch_lessons import arch_lessons

_EXEMPLAR_DIR = Path(
    "/Users/baigm2/Documents/Projects/openAG/.worktrees/"
    "b-round-local-recursive/.architecture/exemplars/insulin-pump"
)

_PROPOSAL_KEYS = {"ops", "rationale", "lesson_type", "subject", "severity"}
_SEVERITY_RANK = {"error": 0, "warn": 1, "info": 2}


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def tmp_repo(tmp_path):
    """A repo with the insulin-pump exemplar openAG model fragments."""
    model_dir = tmp_path / ".architecture" / "model"
    model_dir.mkdir(parents=True)
    for frag in sorted(_EXEMPLAR_DIR.glob("*.v3.yaml")):
        shutil.copy(frag, model_dir / frag.name)
    return tmp_path


@pytest.fixture
def empty_repo(tmp_path):
    """A minimal repo whose model loads but yields no mineable signals.

    ``load_doc`` requires at least one ``*.v3.yaml`` fragment; a single empty
    entity fragment is enough to build a graph that produces no gaps/flags.
    """
    model_dir = tmp_path / ".architecture" / "model"
    model_dir.mkdir(parents=True)
    (model_dir / "empty.v3.yaml").write_text("entities: []\nrelationships: []\n")
    return tmp_path


def test_empty_repo_returns_everything_empty(empty_repo):
    out = _run(arch_lessons(repo_path=str(empty_repo)))
    assert out["ok"] is True
    assert out["digest"] == {"lessons": [], "proposals": []}
    assert out["proposals"] == []


def test_miner_fires_end_to_end_with_ranked_proposals(tmp_repo):
    out = _run(arch_lessons(repo_path=str(tmp_repo)))
    assert out["ok"] is True

    lessons = out["digest"]["lessons"]
    proposals = out["digest"]["proposals"]
    assert len(lessons) >= 1, "exemplar should fire at least one miner"

    # The exemplar carries owed-promise gaps, so the always-error
    # recurring-gap miner must fire (pins the end-to-end gap->lesson path).
    fired_types = {l.get("lesson_type") for l in lessons}
    assert "lesson:recurring-gap" in fired_types

    # proposals surfaced at top level == digest proposals, one per lesson.
    assert out["proposals"] == proposals
    assert len(proposals) == len(lessons)

    # Each proposal stub carries exactly the documented keys.
    for stub in proposals:
        assert _PROPOSAL_KEYS == set(stub.keys())
        assert isinstance(stub["ops"], list)
        assert isinstance(stub["rationale"], str)
        assert stub["severity"] in _SEVERITY_RANK

    # Lessons are ranked: severity (error first), then descending evidence.
    rank_keys = [
        (_SEVERITY_RANK.get(l.get("severity"), 99), -int(l.get("evidence_count", 0)))
        for l in lessons
    ]
    assert rank_keys == sorted(rank_keys)


def test_lessons_persisted_to_jsonl(tmp_repo):
    out = _run(arch_lessons(repo_path=str(tmp_repo)))
    assert out["ok"] is True

    lessons_path = tmp_repo / ".architecture" / "lessons.jsonl"
    assert lessons_path.exists()
    persisted = [
        line for line in lessons_path.read_text().splitlines() if line.strip()
    ]
    # At least one lesson was appended to the store.
    assert len(persisted) >= len(out["digest"]["lessons"]) >= 1


def test_missing_repo_returns_not_found():
    out = _run(arch_lessons(repo_path="/nonexistent/repo/path"))
    assert out["ok"] is False
    assert out["error"]["code"] == "NOT_FOUND"


def test_missing_model_returns_not_found(tmp_path):
    # Repo exists but has no openAG model dir — load_doc raises FileNotFoundError.
    out = _run(arch_lessons(repo_path=str(tmp_path)))
    assert out["ok"] is False
    assert out["error"]["code"] == "NOT_FOUND"


def test_idempotent_shape_on_repeat_call(tmp_repo):
    lessons_path = tmp_repo / ".architecture" / "lessons.jsonl"
    first = _run(arch_lessons(repo_path=str(tmp_repo)))
    after_first = len(
        [l for l in lessons_path.read_text().splitlines() if l.strip()]
    )
    second = _run(arch_lessons(repo_path=str(tmp_repo)))
    after_second = len(
        [l for l in lessons_path.read_text().splitlines() if l.strip()]
    )
    assert first["ok"] is True and second["ok"] is True
    # Shape is stable across calls (digest key set + proposal key sets).
    assert set(first["digest"].keys()) == {"lessons", "proposals"}
    assert set(second["digest"].keys()) == {"lessons", "proposals"}
    for stub in second["proposals"]:
        assert _PROPOSAL_KEYS == set(stub.keys())
    # Dedup: re-mining an unchanged model yields the same subjects and a stable
    # digest view, and the append-only ledger does NOT grow on repeat (extend()
    # skips already-persisted lessons by ts-free content key).
    first_subjects = {l["subject"] for l in first["digest"]["lessons"]}
    second_subjects = {l["subject"] for l in second["digest"]["lessons"]}
    assert first_subjects == second_subjects
    assert len(second["digest"]["lessons"]) == len(first["digest"]["lessons"])
    assert after_second == after_first


def test_self_instruments_journal(tmp_repo):
    _run(arch_lessons(repo_path=str(tmp_repo)))
    from openag.observe import journal

    records = journal.read(tmp_repo)
    assert any(
        r.get("io_kind") == "tool_call" and r.get("name") == "arch_lessons"
        for r in records
    ), "arch_lessons should append its own tool_call observation"
