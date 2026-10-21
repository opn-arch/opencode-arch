"""Shared generation-ledger helper for the round-centric MCP tools.

The diachronic identity ledger lives at ``<repo>/.architecture/generations/``
as one JSON file per monotone 7-digit generation (written by
``arch_commit_generation``). ``arch_history``, ``arch_generation``, and
``arch_lessons`` all need a :class:`~openag.kernel.generations.GenerationStore`
rooted there — this module is the single source of truth for the relative path
and the resolve-repo-then-root factory. Imports of ``openag`` are lazy so the
tools module stays importable without the dependency present.
"""
from __future__ import annotations

import os

from opencode_arch.mcp.envelope import resolve_repo

GENERATIONS_REL = os.path.join(".architecture", "generations")


def generation_store(repo_path: str):
    """Build a GenerationStore rooted under the resolved repo's ledger dir."""
    from openag.kernel.generations import GenerationStore

    resolved = resolve_repo(repo_path)
    root = os.path.join(str(resolved), GENERATIONS_REL)
    return GenerationStore(root=root)
