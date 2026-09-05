"""Stub proposer functions for T16 (architect_job_run) tests.

These functions match the ``proposer(work_order) -> Proposal`` contract
expected by :func:`opencode_arch.lifecycle_exec.worker.run_job`. Tests
reference them by dotted path via the plugin config file.

They live under ``tests/`` and are addressable at the module name
``_proposer_fixtures`` after the test module inserts this directory on
``sys.path``.
"""
from __future__ import annotations


def stub_valid_proposal(_work_order):
    """Return a minimal-valid ``ModelPatch`` for the given work order."""
    from architecture_model.ai.proposals import ModelPatch, Provenance

    return ModelPatch(
        provenance=Provenance(
            work_order_id=_work_order.id,
            model_version="rev-1",
            prompt_digest="digest",
        ),
        operations=[],
    )


# Alias to satisfy the T16 spec name.
stub_valid_slice_proposal = stub_valid_proposal


def stub_raising(_work_order):
    """Always raise ``RuntimeError`` — proves the worker traps proposer errors."""
    raise RuntimeError("stub failure")


def stub_non_proposal(_work_order):
    """Return a dict — proves the worker rejects non-Proposal returns."""
    return {"not": "a proposal"}


def stub_invalid_proposal(_work_order):
    """Return a real ``ModelPatch`` whose provenance intentionally fails
    validation (work_order_id mismatch)."""
    from architecture_model.ai.proposals import ModelPatch, Provenance

    return ModelPatch(
        provenance=Provenance(
            work_order_id="wo-DOES-NOT-MATCH",
            model_version="rev-1",
            prompt_digest="digest",
        ),
        operations=[],
    )


# A non-callable attribute so tests can point a "plugin" at it.
NOT_A_FUNCTION = 42
