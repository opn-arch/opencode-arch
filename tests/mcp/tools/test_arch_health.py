"""Tests for the arch_health B-ROUND context-read MCP tool.

A pure-read wrapper over the openAG kernel health projection following the
OCA envelope convention. Covers graph-wide and per-node health, unknown node
handling, and missing model/repo error mapping.
"""
from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import pytest

from opencode_arch.mcp.tools.arch_health import arch_health

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


def test_arch_health_graph_wide(tmp_repo):
    out = _run(arch_health(repo_path=str(tmp_repo)))
    assert out["ok"] is True
    assert isinstance(out["verdict_counts"], dict)
    assert isinstance(out["worst_offenders"], list)
    assert isinstance(out["silence_index"], float)
    assert isinstance(out["flag_rollup"], dict)


def test_arch_health_node(tmp_repo):
    out = _run(arch_health(repo_path=str(tmp_repo), node_id="CAP-DOSE"))
    assert out["ok"] is True
    assert out["entity_id"] == "CAP-DOSE"
    assert isinstance(out["verdict"], str)
    assert isinstance(out["flags"], list)


def test_arch_health_unknown_node_returns_invalid_argument(tmp_repo):
    out = _run(arch_health(repo_path=str(tmp_repo), node_id="CAP-NOPE"))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_arch_health_missing_model_returns_not_found(tmp_path):
    out = _run(arch_health(repo_path=str(tmp_path)))
    assert out["ok"] is False
    assert out["error"]["code"] == "NOT_FOUND"


def test_arch_health_missing_repo_returns_not_found():
    out = _run(arch_health(repo_path="/nonexistent/repo/path"))
    assert out["ok"] is False
    assert out["error"]["code"] == "NOT_FOUND"


def test_arch_health_tolerates_observations_journal(tmp_repo):
    arch_dir = tmp_repo / ".architecture"
    record = {"entity_id": "CAP-DOSE", "kind": "observation"}
    (arch_dir / "observations.jsonl").write_text(json.dumps(record) + "\n")
    out = _run(arch_health(repo_path=str(tmp_repo), node_id="CAP-DOSE"))
    assert out["ok"] is True
    assert out["entity_id"] == "CAP-DOSE"
