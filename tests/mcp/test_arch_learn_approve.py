"""Tests for the ``arch_learn_approve`` approval-gate-release MCP tool.

``arch_learn`` materializes a draft WorkOrder + Job that STOPS at the
review gate (``draft``). ``arch_learn_approve`` is the gate release:
given that draft ``job_id`` it transitions ``draft → approved → queued``,
runs the job through a proposer (injected in tests, resolved from
``.architecture/ai/proposer_config.yaml`` in production), then applies
and publishes the resulting ModelPatch — the same author→apply→publish
path ``arch_work_issue`` uses, minus the logs-db issue ceremony.

The deterministic ``_valid_proposer`` adds a single isolated component
with a unique id (no relationship), which validates against the
insulin-pump exemplar seeded by ``_seed_model``.
"""
from __future__ import annotations

import asyncio

from opencode_arch.mcp.tools.arch_learn import arch_learn
from opencode_arch.mcp.tools.arch_learn_approve import arch_learn_approve


def _run(coro):
    return asyncio.run(coro)


def _valid_proposer(_wo):
    """Add one isolated component — valid against the seeded exemplar."""
    return {
        "ops": [
            {
                "kind": "add",
                "target": "entity",
                "entity_kind": "components",
                "value": {
                    "id": "COMP-APPROVE-TEST",
                    "name": "Approve Test",
                    "kind": "Component",
                },
            }
        ]
    }


def _bogus_proposer(_wo):
    """Return a non-ModelPatch object — fails the job in the worker."""
    return {"bogus": 1}


def _draft_job(repo, _seed_model) -> str:
    """Seed the exemplar and materialize a draft Job via arch_learn."""
    _seed_model(repo)
    env = _run(arch_learn(repo_path=str(repo)))
    assert env["ok"] is True
    assert env["job_state"] == "draft"
    return env["job_id"]


def test_arch_learn_approve_applies_with_mock_proposer(tmp_path, _seed_model):
    job_id = _draft_job(tmp_path, _seed_model)
    env = _run(
        arch_learn_approve(
            repo_path=str(tmp_path), job_id=job_id, proposer=_valid_proposer
        )
    )
    assert env["ok"] is True
    assert env["job_state"] == "completed"
    assert env["applied"] is True
    assert env["package_revision_to"]
    assert env["model_diff_digest"]


def test_arch_learn_approve_dry_run_does_not_publish(tmp_path, _seed_model):
    job_id = _draft_job(tmp_path, _seed_model)
    env = _run(
        arch_learn_approve(
            repo_path=str(tmp_path),
            job_id=job_id,
            dry_run=True,
            proposer=_valid_proposer,
        )
    )
    assert env["ok"] is True
    assert env["job_state"] == "completed"
    assert env["applied"] is False
    assert env["package_revision_to"] is None
    assert env["model_diff_digest"]


def test_arch_learn_approve_failed_proposer_soft_envelope(tmp_path, _seed_model):
    job_id = _draft_job(tmp_path, _seed_model)
    env = _run(
        arch_learn_approve(
            repo_path=str(tmp_path), job_id=job_id, proposer=_bogus_proposer
        )
    )
    assert env["ok"] is True
    assert env["job_state"] == "failed"
    assert env["applied"] is False
    assert env["error"]


def test_arch_learn_approve_requires_job_id(tmp_path, _seed_model):
    _seed_model(tmp_path)
    env = _run(arch_learn_approve(repo_path=str(tmp_path), job_id=""))
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_arch_learn_approve_unknown_job_returns_not_found(tmp_path, _seed_model):
    _seed_model(tmp_path)
    env = _run(
        arch_learn_approve(
            repo_path=str(tmp_path),
            job_id="job-does-not-exist",
            proposer=_valid_proposer,
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"]["reason"] == "job_missing"
