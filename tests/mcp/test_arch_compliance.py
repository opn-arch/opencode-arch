"""Tests for the ``arch_compliance`` MCP tool.

``arch_compliance`` exposes openAG's three compliance reports behind the
OCA envelope: the static standard-mandate coverage ``matrix``, the
per-axis relationship-exploration ``axes`` report (over the model doc),
and a gap-derived 0-100 ``scoring`` projection (gaps emitted over the
real entity nodes, mirroring ``arch_lessons``).
"""
from __future__ import annotations

import asyncio

from opencode_arch.mcp.tools.arch_compliance import arch_compliance


def test_arch_compliance_matrix(tmp_path, _seed_model):
    _seed_model(tmp_path)
    env = asyncio.run(arch_compliance(repo_path=str(tmp_path), report="matrix"))
    assert env["ok"] is True and isinstance(env["matrix"], list)


def test_arch_compliance_axes(tmp_path, _seed_model):
    _seed_model(tmp_path)
    env = asyncio.run(arch_compliance(repo_path=str(tmp_path), report="axes"))
    assert env["ok"] is True and isinstance(env["axes"], list)


def test_arch_compliance_scoring(tmp_path, _seed_model):
    _seed_model(tmp_path)
    env = asyncio.run(arch_compliance(repo_path=str(tmp_path), report="scoring"))
    assert env["ok"] is True and 0 <= env["score"]["score"] <= 100


def test_arch_compliance_bad_report(tmp_path, _seed_model):
    _seed_model(tmp_path)
    env = asyncio.run(arch_compliance(repo_path=str(tmp_path), report="nope"))
    assert env["ok"] is False and env["error"]["code"] == "INVALID_ARGUMENT"
