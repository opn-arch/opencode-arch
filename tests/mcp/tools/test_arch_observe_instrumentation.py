"""Tests for proprioceptive instrumentation of the OCA ``arch_*`` tools.

Verifies that repo-scoped tool handlers (a) emit a ``tool_call`` observation
tagged ``oca:<handler>`` and (b) bind the repo observation context so
downstream openAG kernel emits land in the same journal — all without
changing the tool's success/failure outcome.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest

from openag.observe.journal import read as read_journal

from opencode_arch.mcp.tools.arch_context import arch_frontier
from opencode_arch.mcp.tools.arch_round import arch_round

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


def test_arch_frontier_emits_tool_call_observation(tmp_repo):
    out = _run(arch_frontier(repo_path=str(tmp_repo)))
    assert out["ok"] is True

    records = read_journal(tmp_repo)
    tool_calls = [
        r
        for r in records
        if r.get("component_id") == "oca:arch_frontier"
        and r.get("io_kind") == "tool_call"
    ]
    assert tool_calls, f"no oca:arch_frontier tool_call observation in {records!r}"


def test_bad_repo_still_errors_without_exception(tmp_path):
    bad = tmp_path / "nonexistent" / "path" / "xyz"
    out = _run(arch_frontier(repo_path=str(bad)))
    # Instrumentation must not change the error behavior: envelope error,
    # no exception escaped.
    assert out["ok"] is False


def test_arch_round_binds_context_for_downstream_kernel_emits(tmp_repo):
    out = _run(arch_round(repo_path=str(tmp_repo)))
    assert out["ok"] is True

    records = read_journal(tmp_repo)
    tool_calls = [
        r for r in records if r.get("component_id") == "oca:arch_round"
    ]
    assert tool_calls, f"no oca:arch_round observation in {records!r}"

    kernel_emits = [
        r
        for r in records
        if str(r.get("component_id", "")).startswith("COMP-")
    ]
    assert kernel_emits, f"no downstream COMP- kernel observation in {records!r}"
