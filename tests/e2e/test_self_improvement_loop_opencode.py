"""Opt-in, real-OpenCode e2e of the closed self-improvement loop.

Mirrors ``test_self_improvement_loop.py`` but resolves a REAL
OpenCode-backed proposer from ``.architecture/ai/proposer_config.yaml``
instead of injecting a Python function. Collected-but-SKIPPED by default;
only runs when ``OPENCODE_LIVE`` is set in the environment.
"""
from __future__ import annotations

import asyncio
import os

import pytest

from opencode_arch.mcp.tools.arch_learn import arch_learn
from opencode_arch.mcp.tools.arch_learn_approve import arch_learn_approve
from openag.lifecycle.package import load_generation


def _run(coro):
    return asyncio.run(coro)


@pytest.mark.opencode_live
@pytest.mark.skipif(
    not os.environ.get("OPENCODE_LIVE"),
    reason="opt-in real-OpenCode e2e",
)
def test_closed_loop_applies_patch_opencode(tmp_path, _seed_model):
    repo = tmp_path
    _seed_model(repo)

    # Point the dev-loop at the real-OpenCode proposer plugin.
    cfg_dir = repo / ".architecture" / "ai"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "proposer_config.yaml").write_text(
        'plugin: "opencode_arch.devloop.opencode_proposer:propose"\n',
        encoding="utf-8",
    )

    learn_env = _run(arch_learn(repo_path=str(repo)))
    assert learn_env["ok"] is True
    assert learn_env["job_state"] == "draft"
    job_id = learn_env["job_id"]

    # proposer=None -> resolved from proposer_config.yaml (real OpenCode).
    approve_env = _run(arch_learn_approve(repo_path=str(repo), job_id=job_id))
    assert approve_env["ok"] is True
    assert approve_env["job_state"] == "completed"
    assert approve_env["applied"] is True
    assert approve_env["package_revision_to"]

    gen = load_generation(str(repo))
    entities = gen["generation"]["entities"]
    ids = {e.get("id") for e in entities}
    assert "COMP-OPENCODE-LIVE" in ids
