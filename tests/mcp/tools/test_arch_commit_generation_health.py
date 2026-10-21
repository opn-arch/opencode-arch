"""Tests for arch_commit_generation recording a health projection.

Phase 2 ("look back") proprioception: committing a generation now computes
the graph-wide ``graph_health`` projection and both RETURNS it and RECORDS
it on disk alongside the generation.
"""
from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import pytest

from opencode_arch.mcp.tools.arch_generation import arch_commit_generation

_EXEMPLAR_DIR = Path(
    "/Users/baigm2/Documents/Projects/openAG/.worktrees/"
    "b-round-local-recursive/.architecture/exemplars/insulin-pump"
)

_HEALTH_KEYS = {"verdict_counts", "worst_offenders", "silence_index", "flag_rollup"}


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


def test_commit_returns_health_and_gen_id(tmp_repo):
    out = _run(arch_commit_generation(repo_path=str(tmp_repo)))
    assert out["ok"] is True
    assert isinstance(out["gen_id"], str)
    assert len(out["gen_id"]) == 7 and out["gen_id"].isdigit()
    assert isinstance(out["entity_count"], int)
    assert out["entity_count"] > 0
    assert isinstance(out["health"], dict)
    assert _HEALTH_KEYS.issubset(out["health"].keys())


def test_recorded_generation_on_disk_contains_health(tmp_repo):
    out = _run(arch_commit_generation(repo_path=str(tmp_repo)))
    gen_id = out["gen_id"]

    gen_path = tmp_repo / ".architecture" / "generations" / f"{gen_id}.json"
    assert gen_path.exists()
    recorded = json.loads(gen_path.read_text())
    assert "health" in recorded
    assert recorded["health"] == out["health"]


def test_commit_with_seeded_observations(tmp_repo):
    # Smoke test: a well-formed observations journal is read without error and
    # still yields a well-formed graph_health projection. (A single observation
    # on an already-gapped node does not shift the graph-level verdict counts —
    # graph_health is deliberately dominated by structural gaps — so this
    # asserts tolerance + shape, not a verdict differential.)
    obs_path = tmp_repo / ".architecture" / "observations.jsonl"
    obs_path.write_text(
        json.dumps(
            {
                "component_id": "CAP-DOSE",
                "io_kind": "tool_call",
                "direction": "in",
                "name": "deliver_dose",
                "payload_digest": "",
                "ts": "2026-01-01T00:00:00+00:00",
            }
        )
        + "\n"
    )
    out = _run(arch_commit_generation(repo_path=str(tmp_repo)))
    assert out["ok"] is True
    assert _HEALTH_KEYS.issubset(out["health"].keys())
