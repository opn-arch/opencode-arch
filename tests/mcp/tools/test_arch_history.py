"""Tests for arch_history — the diachronic generation-ledger read surface.

Phase 2 ("look back") proprioception: ``arch_history`` is a pure-read tool
over the health-enriched :class:`~openag.kernel.generations.GenerationStore`
written by ``arch_commit_generation``. It exposes three modes:

* timeline (no args) — concise per-generation rollup,
* trajectory (``node_id``) — a node's verdict history across generations,
* diff (``gen_a`` + ``gen_b``) — the semantic diff between two generations.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest

from opencode_arch.mcp.tools.arch_generation import arch_commit_generation
from opencode_arch.mcp.tools.arch_history import arch_history

_EXEMPLAR_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "exemplars" / "insulin-pump"

_TIMELINE_KEYS = {
    "gen_id",
    "entity_count",
    "verdict_counts",
    "silence_index",
    "flag_rollup",
}
_DIFF_KEYS = {
    "appeared",
    "disappeared",
    "verdict_transitions",
    "flag_delta",
    "verdict_count_delta",
}


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


def _commit(repo, n=1):
    for _ in range(n):
        out = _run(arch_commit_generation(repo_path=str(repo)))
        assert out["ok"] is True


def test_timeline_mode(tmp_repo):
    _commit(tmp_repo, n=2)
    out = _run(arch_history(repo_path=str(tmp_repo)))
    assert out["ok"] is True
    assert out["mode"] == "timeline"
    gens = out["generations"]
    assert isinstance(gens, list)
    assert len(gens) == 2
    for entry in gens:
        assert _TIMELINE_KEYS == set(entry.keys())
        assert entry["entity_count"] > 0


def test_trajectory_mode(tmp_repo):
    _commit(tmp_repo, n=2)
    out = _run(arch_history(repo_path=str(tmp_repo), node_id="CAP-DOSE"))
    assert out["ok"] is True
    assert out["mode"] == "trajectory"
    assert out["node_id"] == "CAP-DOSE"
    history = out["history"]
    assert isinstance(history, list)
    assert len(history) == 2
    for entry in history:
        assert set(entry.keys()) == {"gen_id", "verdict"}


def test_trajectory_mode_unknown_node(tmp_repo):
    _commit(tmp_repo, n=1)
    out = _run(arch_history(repo_path=str(tmp_repo), node_id="NOPE-404"))
    assert out["ok"] is True
    assert out["mode"] == "trajectory"
    assert out["history"] == []


def test_diff_mode(tmp_repo):
    _commit(tmp_repo, n=2)
    out = _run(
        arch_history(repo_path=str(tmp_repo), gen_a="0000001", gen_b="0000002")
    )
    assert out["ok"] is True
    assert out["mode"] == "diff"
    assert out["gen_a"] == "0000001"
    assert out["gen_b"] == "0000002"
    assert _DIFF_KEYS == set(out["diff"].keys())


def test_diff_mode_unknown_gen(tmp_repo):
    _commit(tmp_repo, n=1)
    out = _run(
        arch_history(repo_path=str(tmp_repo), gen_a="0000001", gen_b="9999999")
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_exactly_one_gen_guard(tmp_repo):
    _commit(tmp_repo, n=1)
    out = _run(arch_history(repo_path=str(tmp_repo), gen_a="0000001"))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_bad_node_id(tmp_repo):
    _commit(tmp_repo, n=1)
    out = _run(arch_history(repo_path=str(tmp_repo), node_id=""))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_bad_gen_id(tmp_repo):
    # Empty-string gen ids hit the up-front guard, not the diff path.
    _commit(tmp_repo, n=1)
    out = _run(arch_history(repo_path=str(tmp_repo), gen_a="", gen_b="0000001"))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_diff_takes_precedence_over_trajectory(tmp_repo):
    # When node_id AND both gens are given, diff wins and node_id is ignored.
    _commit(tmp_repo, n=2)
    out = _run(
        arch_history(
            repo_path=str(tmp_repo),
            node_id="CAP-DOSE",
            gen_a="0000001",
            gen_b="0000002",
        )
    )
    assert out["ok"] is True
    assert out["mode"] == "diff"
    assert "node_id" not in out
    assert _DIFF_KEYS == set(out["diff"].keys())
