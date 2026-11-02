"""Shared fixtures for the ``tests/mcp`` suite.

Hosts the canonical ``_seed_model`` fixture used by the openAG-native
``arch_*`` tool tests (grow / mine / compliance). It writes the
insulin-pump exemplar openAG model fragments (root ``System``
``SYS-INSULIN-PUMP``) into ``<repo>/.architecture/model/`` and returns
the repo path, so a seeded repo carries a real entity graph with gaps.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

_EXEMPLAR_DIR = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "exemplars"
    / "insulin-pump"
)


@pytest.fixture
def _seed_model():
    """Return a seeder that writes the insulin-pump openAG model fragments."""

    def _seed(repo: Path) -> Path:
        model_dir = Path(repo) / ".architecture" / "model"
        model_dir.mkdir(parents=True, exist_ok=True)
        for frag in sorted(_EXEMPLAR_DIR.glob("*.v3.yaml")):
            shutil.copy(frag, model_dir / frag.name)
        return Path(repo)

    return _seed


@pytest.fixture
def _seed_model_with_signals(_seed_model):
    """Seed a repo whose model mines >= 1 lesson.

    The insulin-pump exemplar carries owed-promise gaps, so the
    always-error ``lesson:recurring-gap`` miner fires on the seeded
    model alone (no generation history needed) — enough signal for a
    lesson-materialization gate to pick a top lesson.
    """

    def _seed(repo: Path) -> Path:
        return _seed_model(Path(repo))

    return _seed
