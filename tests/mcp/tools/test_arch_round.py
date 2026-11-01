"""Tests for the G2 ``arch_round`` MCP tool.

An idempotent, node-scoped (or whole-graph) run of the B-ROUND
least-fixpoint, following the OCA envelope convention. Pure read:
``b_round`` mutates only the in-memory graph and writes nothing to disk.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest

from opencode_arch.mcp.tools.arch_round import arch_round

_EXEMPLAR_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "exemplars" / "insulin-pump"


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


def test_arch_round_is_idempotent(tmp_repo):
    a = _run(arch_round(repo_path=str(tmp_repo), node_id="CAP-DOSE"))
    b = _run(arch_round(repo_path=str(tmp_repo), node_id="CAP-DOSE"))
    assert a["ok"] is True
    assert b["ok"] is True
    assert a["grounded_digest"] == b["grounded_digest"]


def test_arch_round_whole_graph(tmp_repo):
    out = _run(arch_round(repo_path=str(tmp_repo)))
    assert out["ok"] is True
    assert isinstance(out["grounded"], list)
    assert isinstance(out["grounded_digest"], str)
    assert "converged" in out
    assert "iterations" in out
    assert "ungrounded" in out
    assert "gaps" in out


def test_arch_round_whole_graph_is_idempotent(tmp_repo):
    a = _run(arch_round(repo_path=str(tmp_repo)))
    b = _run(arch_round(repo_path=str(tmp_repo)))
    assert a["grounded_digest"] == b["grounded_digest"]


def test_arch_round_node_scope_subset(tmp_repo):
    whole = _run(arch_round(repo_path=str(tmp_repo)))
    scoped = _run(arch_round(repo_path=str(tmp_repo), node_id="CAP-DOSE"))
    assert whole["ok"] is True
    assert scoped["ok"] is True
    assert set(scoped["grounded"]).issubset(set(whole["grounded"]))


def test_arch_round_node_scope_non_vacuous(tmp_repo):
    """A node that actually owns a grounded promise yields a non-empty,
    proper subset of the whole-graph grounded set."""
    whole = _run(arch_round(repo_path=str(tmp_repo)))
    scoped = _run(arch_round(repo_path=str(tmp_repo), node_id="CON-OVERDOSE"))
    assert scoped["ok"] is True
    assert scoped["grounded"], "expected CON-OVERDOSE to own a grounded promise"
    assert set(scoped["grounded"]).issubset(set(whole["grounded"]))
    assert set(scoped["grounded"]) != set(whole["grounded"])


def test_arch_round_unknown_node_errors(tmp_repo):
    out = _run(arch_round(repo_path=str(tmp_repo), node_id="CAP-NOPE"))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_arch_round_empty_node_id_errors(tmp_repo):
    out = _run(arch_round(repo_path=str(tmp_repo), node_id="   "))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_arch_round_missing_model_returns_not_found(tmp_path):
    out = _run(arch_round(repo_path=str(tmp_path)))
    assert out["ok"] is False
    assert out["error"]["code"] == "NOT_FOUND"


def test_arch_round_missing_repo_returns_not_found():
    out = _run(arch_round(repo_path="/nonexistent/repo/path"))
    assert out["ok"] is False
    assert out["error"]["code"] == "NOT_FOUND"
