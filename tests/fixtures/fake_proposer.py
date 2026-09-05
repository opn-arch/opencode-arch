"""Fake proposer callables for testing the work-issue orchestrator.

Real LLM-backed proposers land in Plan B via LLMProvider. These fakes let
Plan A tests exercise the orchestration without external dependencies.
"""

from __future__ import annotations

from architecture_model.ai.proposals import ModelPatch, Provenance
from architecture_model.ai.work_order import WorkOrder


def make_noop_valid_proposer(*, model_version: str):
    """Returns a valid, empty ModelPatch pinned to the given model_version (root_digest)."""
    def _proposer(wo: WorkOrder):
        return ModelPatch(
            provenance=Provenance(
                work_order_id=wo.id,
                model_version=model_version,
                prompt_digest="sha256:" + "a" * 64,
            ),
            operations=[],
        )
    return _proposer


def make_invalid_proposer():
    """Returns a non-Proposal object; worker will mark job failed."""
    def _proposer(wo: WorkOrder):
        return "not-a-proposal"
    return _proposer
