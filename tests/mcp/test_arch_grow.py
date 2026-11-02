"""Tests for the ``arch_grow`` MCP tool.

``arch_grow`` exposes openAG's standalone scoped forward-GROW operator
behind the OCA envelope. The ``no_provider=True`` path threads
``provider=None`` through ``forward_grow`` → ``b_round`` for a
deterministic, pure-symbolic run (no LLM) suitable for tests.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest

from opencode_arch.mcp.tools.arch_grow import arch_grow

_EXEMPLAR_DIR = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "exemplars"
    / "insulin-pump"
)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def _seed_model(tmp_path):
    """Return a seeder that writes the insulin-pump openAG model fragments.

    The exemplar carries a root ``System`` ``SYS-INSULIN-PUMP``.
    """

    def _seed(repo: Path) -> Path:
        model_dir = Path(repo) / ".architecture" / "model"
        model_dir.mkdir(parents=True, exist_ok=True)
        for frag in sorted(_EXEMPLAR_DIR.glob("*.v3.yaml")):
            shutil.copy(frag, model_dir / frag.name)
        return Path(repo)

    return _seed


def test_arch_grow_no_provider_returns_root_and_gaps(tmp_path, _seed_model):
    _seed_model(tmp_path)
    env = _run(
        arch_grow(
            repo_path=str(tmp_path),
            root="SYS-INSULIN-PUMP",
            no_provider=True,
        )
    )
    assert env["ok"] is True
    assert env["root"] == "SYS-INSULIN-PUMP"
    assert "gaps" in env and "residue" in env
    assert "a4_grounded" in env and "identity_gaps" in env


def test_arch_grow_no_provider_is_deterministic(tmp_path, _seed_model):
    _seed_model(tmp_path)
    a = _run(arch_grow(repo_path=str(tmp_path), root="SYS-INSULIN-PUMP",
                       no_provider=True))
    b = _run(arch_grow(repo_path=str(tmp_path), root="SYS-INSULIN-PUMP",
                       no_provider=True))
    assert a == b


def test_arch_grow_empty_root_errors(tmp_path, _seed_model):
    _seed_model(tmp_path)
    env = _run(arch_grow(repo_path=str(tmp_path), root="", no_provider=True))
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_arch_grow_missing_model_returns_not_found(tmp_path):
    env = _run(arch_grow(repo_path=str(tmp_path), root="SYS-INSULIN-PUMP",
                         no_provider=True))
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
