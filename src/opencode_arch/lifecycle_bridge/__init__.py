"""Thin re-export layer for architecture-model-standard Phase 1 public surface.

Centralizes lifecycle + AI imports so Phase 2 MCP tools have a single
seam if the upstream API moves.
"""
from __future__ import annotations

from architecture_model.lifecycle.versions import SchemaVersions as _SV

if getattr(_SV, "WORK_ORDER", None) != "1.0.0":
    raise ImportError(
        "opencode_arch.lifecycle_bridge requires architecture-model-standard Phase 1 "
        f"(SchemaVersions.WORK_ORDER == '1.0.0'); got {getattr(_SV, 'WORK_ORDER', None)!r}. "
        "Ensure PYTHONPATH includes the Phase 1 worktree src/."
    )

SchemaVersions = _SV

# Lifecycle: package.
# NOTE: Phase 1 exposes ``ArchitecturePackage`` (Pydantic model) and a
# ``load_package`` function; there is no ``PackageDescriptor``/``PackageLoader``
# class pair. We alias for a stable bridge surface.
from architecture_model.lifecycle.package import (  # noqa: E402
    ArchitecturePackage as PackageDescriptor,
    load_package as PackageLoader,
)
# atomic_store exposes free functions, not a class. Alias the module as a
# namespace so callers can do ``AtomicStore.write_atomic(...)``.
from architecture_model.lifecycle import atomic_store as AtomicStore  # noqa: E402
from architecture_model.lifecycle.journal import Journal  # noqa: E402
from architecture_model.lifecycle.model_slice import ModelSlice  # noqa: E402
# model_slice_materializer exposes ``materialize`` + ``MaterializedSlice``;
# expose the module as a namespace under the ``ModelSliceMaterializer`` name.
from architecture_model.lifecycle import (  # noqa: E402
    model_slice_materializer as ModelSliceMaterializer,
)
from architecture_model.lifecycle.view_spec import ViewSpec  # noqa: E402
from architecture_model.lifecycle.artifact_spec import ArtifactSpec  # noqa: E402
from architecture_model.lifecycle.artifact_dag import ArtifactDAG  # noqa: E402

# AI.
from architecture_model.ai.work_order import WorkOrder  # noqa: E402
from architecture_model.ai.proposals import (  # noqa: E402
    PROPOSAL_TYPES,
    Proposal,
    proposal_from_dict,
)
from architecture_model.ai.jobs import (  # noqa: E402
    InvalidTransitionError,
    Job,
    JobState,
    JobStore,
)
from architecture_model.ai.validators import (  # noqa: E402
    ValidationReport,
    validate as validate_proposal,
)

__all__ = [
    "SchemaVersions",
    "PackageDescriptor",
    "PackageLoader",
    "AtomicStore",
    "Journal",
    "ModelSlice",
    "ModelSliceMaterializer",
    "ViewSpec",
    "ArtifactSpec",
    "ArtifactDAG",
    "WorkOrder",
    "Proposal",
    "PROPOSAL_TYPES",
    "proposal_from_dict",
    "Job",
    "JobState",
    "JobStore",
    "InvalidTransitionError",
    "validate_proposal",
    "ValidationReport",
]
