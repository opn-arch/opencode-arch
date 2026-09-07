"""Stub proposer resolvable via proposer_config.yaml plugin ref.

Reads the target model_version from the STUB_PROPOSER_MODEL_VERSION env var
so the test can pin the proposal to the currently-published root_digest.
"""

from __future__ import annotations

import os

from architecture_model.ai.proposals import ModelPatch, Provenance
from architecture_model.ai.work_order import WorkOrder


def noop_proposer(wo: WorkOrder) -> ModelPatch:
    version = os.environ.get("STUB_PROPOSER_MODEL_VERSION")
    if not version:
        raise RuntimeError("STUB_PROPOSER_MODEL_VERSION not set")
    return ModelPatch(
        provenance=Provenance(
            work_order_id=wo.id,
            model_version=version,
            prompt_digest="sha256:" + "a" * 64,
        ),
        operations=[],
    )
