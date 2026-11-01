"""Tests for the G5 identity/generation tools ``arch_bind`` and
``arch_commit_generation``.

``arch_commit_generation`` records an identity projection of the current model
into the diachronic ``GenerationStore`` (``.architecture/generations/``);
``arch_bind`` runs the θ-crosswalk of the latest generation onto the current
model and surfaces the identity verdict (bind/ambiguous/new + orphans/gaps).
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest

from opencode_arch.mcp.tools.arch_generation import (
    arch_bind,
    arch_commit_generation,
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


def test_commit_then_bind_roundtrip_binds_sticky(tmp_repo):
    committed = _run(arch_commit_generation(repo_path=str(tmp_repo)))
    assert committed["ok"] is True
    assert committed["gen_id"] == "0000001"

    out = _run(arch_bind(repo_path=str(tmp_repo)))
    assert out["ok"] is True
    assert "ambiguous" in out
    # identical model → every entity binds via sticky anchors
    assert len(out["sticky"]) > 0
    assert out["orphans"] == []


def test_bind_with_no_prior_generation_all_new(tmp_repo):
    out = _run(arch_bind(repo_path=str(tmp_repo)))
    assert out["ok"] is True
    assert "ambiguous" in out
    assert out["ambiguous"] == []
    assert out["sticky"] == []
    assert out["entries"]
    assert all(e["band"] == "new" for e in out["entries"])


def test_commit_generation_returns_monotone_gen_id(tmp_repo):
    first = _run(arch_commit_generation(repo_path=str(tmp_repo)))
    second = _run(arch_commit_generation(repo_path=str(tmp_repo)))
    assert first["gen_id"] == "0000001"
    assert second["gen_id"] == "0000002"
    assert first["entity_count"] > 0
    assert second["entity_count"] == first["entity_count"]
