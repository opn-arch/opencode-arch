"""End-to-end test of the full closed self-improvement loop.

Drives the complete loop with a deterministic injected proposer and NO
network:

    seed model -> arch_learn (draft) -> arch_learn_approve (completed/applied)
    -> reload the published generation -> assert the proposer's patch landed

The deterministic ``_valid_proposer`` adds a single isolated component
(``COMP-APPROVE-TEST``) that validates against the seeded insulin-pump
exemplar. ``arch_learn_approve`` publishes a new generation; the applied
component is visible via ``openag.lifecycle.package.load_generation`` (NOT
via ``load_model_dir`` on the working model dir, which is not rewritten in
place). Determinism is asserted by running the whole loop twice in two
fresh repos and comparing the resulting ``model_diff_digest`` values.
"""
from __future__ import annotations

import asyncio

from opencode_arch.mcp.tools.arch_learn import arch_learn
from opencode_arch.mcp.tools.arch_learn_approve import arch_learn_approve
from openag.lifecycle.package import load_generation


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


def _drive_loop(repo, seed) -> dict:
    """Seed, run arch_learn (draft) then arch_learn_approve (applied).

    Returns the approve envelope.
    """
    seed(repo)

    learn_env = _run(arch_learn(repo_path=str(repo)))
    assert learn_env["ok"] is True
    assert learn_env["job_state"] == "draft"
    job_id = learn_env["job_id"]

    approve_env = _run(
        arch_learn_approve(
            repo_path=str(repo), job_id=job_id, proposer=_valid_proposer
        )
    )
    assert approve_env["ok"] is True
    assert approve_env["job_state"] == "completed"
    assert approve_env["applied"] is True
    assert approve_env["package_revision_to"]
    return approve_env


def test_closed_loop_applies_patch(tmp_path, _seed_model):
    env = _drive_loop(tmp_path, _seed_model)

    assert env["package_revision_to"]
    assert env["model_diff_digest"].startswith("sha256:")

    # The working .architecture/model/ dir is NOT rewritten in place by
    # approve — the applied patch lives in the newly published generation.
    gen = load_generation(str(tmp_path))
    entities = gen["generation"]["entities"]
    ids = {e.get("id") for e in entities}
    assert "COMP-APPROVE-TEST" in ids


def test_closed_loop_is_deterministic(tmp_path, _seed_model):
    repo_a = tmp_path / "run_a"
    repo_b = tmp_path / "run_b"
    repo_a.mkdir(parents=True)
    repo_b.mkdir(parents=True)

    env_a = _drive_loop(repo_a, _seed_model)
    env_b = _drive_loop(repo_b, _seed_model)

    assert env_a["model_diff_digest"] == env_b["model_diff_digest"]
