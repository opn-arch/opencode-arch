"""Tests for the shared ``_generations`` tool helper (DRY cleanup).

``GENERATIONS_REL`` + ``generation_store`` were previously duplicated across
``arch_history``, ``arch_generation``, and ``arch_lessons``. This locks the
single source of truth: the relative ledger path and a factory that resolves
the repo and roots a :class:`~openag.kernel.generations.GenerationStore` under
``<repo>/.architecture/generations/``.
"""
from __future__ import annotations

import os

from opencode_arch.mcp.tools._generations import GENERATIONS_REL, generation_store


def test_generations_rel_constant():
    assert GENERATIONS_REL == os.path.join(".architecture", "generations")


def test_generation_store_roots_under_resolved_repo(tmp_path):
    store = generation_store(str(tmp_path))
    assert store.root == os.path.join(str(tmp_path), GENERATIONS_REL)
    # An empty repo ledger starts empty and records monotone 7-digit ids.
    assert store.all() == []
