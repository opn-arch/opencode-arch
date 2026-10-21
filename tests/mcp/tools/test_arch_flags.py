"""Tests for the arch_flags B-ROUND context-read MCP tool.

A pure-read anomaly surface over the openAG kernel's ``audit_observations``
following the OCA envelope convention. Covers workspace-wide and node-filtered
flags, unknown node handling, missing model/repo error mapping, and the
observations-journal read path.
"""
from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import pytest

from opencode_arch.mcp.tools.arch_flags import arch_flags

_EXEMPLAR_DIR = Path(
    "/Users/baigm2/Documents/Projects/openAG/.worktrees/"
    "b-round-local-recursive/.architecture/exemplars/insulin-pump"
)


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


def test_arch_flags_workspace_wide(tmp_repo):
    out = _run(arch_flags(repo_path=str(tmp_repo)))
    assert out["ok"] is True
    assert isinstance(out["flags"], list)
    for f in out["flags"]:
        assert isinstance(f, dict)
        assert set(("flag_type", "component_id", "detail", "severity")) <= set(f)


def test_arch_flags_node_filtered(tmp_repo):
    all_out = _run(arch_flags(repo_path=str(tmp_repo)))
    out = _run(arch_flags(repo_path=str(tmp_repo), node_id="CAP-DOSE"))
    assert out["ok"] is True
    assert isinstance(out["flags"], list)
    assert all(f["component_id"] == "CAP-DOSE" for f in out["flags"])
    # filtered result is exactly the workspace-wide set reduced to this node
    # (robust to exemplar churn, and proves the filter actually does something)
    assert out["flags"] == [
        f for f in all_out["flags"] if f["component_id"] == "CAP-DOSE"
    ]


def test_arch_flags_unknown_node_returns_invalid_argument(tmp_repo):
    out = _run(arch_flags(repo_path=str(tmp_repo), node_id="CAP-NOPE"))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_arch_flags_missing_model_returns_not_found(tmp_path):
    out = _run(arch_flags(repo_path=str(tmp_path)))
    assert out["ok"] is False
    assert out["error"]["code"] == "NOT_FOUND"


def test_arch_flags_missing_repo_returns_not_found():
    out = _run(arch_flags(repo_path="/nonexistent/repo/path"))
    assert out["ok"] is False
    assert out["error"]["code"] == "NOT_FOUND"


def test_arch_flags_tolerates_observations_journal(tmp_repo):
    arch_dir = tmp_repo / ".architecture"
    record = {"entity_id": "CAP-DOSE", "kind": "observation"}
    (arch_dir / "observations.jsonl").write_text(json.dumps(record) + "\n")
    out = _run(arch_flags(repo_path=str(tmp_repo), node_id="CAP-DOSE"))
    assert out["ok"] is True
    assert isinstance(out["flags"], list)
