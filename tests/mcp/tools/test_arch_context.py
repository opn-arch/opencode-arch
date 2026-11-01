"""Tests for the G1 round-centric context-read MCP tools.

Covers arch_frontier / arch_owed / arch_gaps / arch_slice — four pure-read
wrappers over the openAG kernel following the OCA envelope convention.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest

from opencode_arch.mcp.tools.arch_context import (
    arch_frontier,
    arch_gaps,
    arch_owed,
    arch_slice,
)

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


def test_arch_frontier_returns_ready_nodes(tmp_repo):
    out = _run(arch_frontier(repo_path=str(tmp_repo)))
    assert out["ok"] is True
    assert isinstance(out["frontier"], list)
    assert all(isinstance(nid, str) for nid in out["frontier"])


def test_arch_owed_returns_valence_gap(tmp_repo):
    out = _run(arch_owed(repo_path=str(tmp_repo), node_id="CAP-DOSE"))
    assert out["ok"] is True
    assert isinstance(out["owed"], dict)
    # non-empty keys are attribute strings mapped to valence strings
    for attr, valence in out["owed"].items():
        assert isinstance(attr, str)
        assert isinstance(valence, str)


def test_arch_gaps_returns_list(tmp_repo):
    out = _run(arch_gaps(repo_path=str(tmp_repo), node_id="CAP-DOSE"))
    assert out["ok"] is True
    assert isinstance(out["gaps"], list)
    assert all(isinstance(gap, dict) for gap in out["gaps"])


def test_arch_slice_returns_subdoc(tmp_repo):
    out = _run(arch_slice(repo_path=str(tmp_repo), node_id="CAP-DOSE"))
    assert out["ok"] is True
    assert isinstance(out["slice"], dict)
    # the entity-scoped sub-doc references the requested entity
    assert "CAP-DOSE" in repr(out["slice"])


def test_arch_owed_unknown_node_returns_invalid_argument(tmp_repo):
    out = _run(arch_owed(repo_path=str(tmp_repo), node_id="CAP-NOPE"))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_arch_slice_unknown_node_returns_invalid_argument(tmp_repo):
    out = _run(arch_slice(repo_path=str(tmp_repo), node_id="CAP-NOPE"))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_arch_frontier_missing_model_returns_not_found(tmp_path):
    # repo exists but has no .architecture/model dir
    out = _run(arch_frontier(repo_path=str(tmp_path)))
    assert out["ok"] is False
    assert out["error"]["code"] == "NOT_FOUND"


def test_arch_gaps_missing_repo_returns_not_found():
    out = _run(arch_gaps(repo_path="/nonexistent/repo/path", node_id="CAP-DOSE"))
    assert out["ok"] is False
    assert out["error"]["code"] == "NOT_FOUND"
