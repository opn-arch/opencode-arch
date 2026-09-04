"""MCP tool: materialize a ModelSlice contract against the root package.

Wraps ``architecture_model.lifecycle.model_slice_materializer.materialize``
to expose a stable envelope-shaped API for LLMs.

Deviations vs. spec
-------------------
* ``scope == "federated"`` is rejected at the tool boundary with
  ``PRECONDITION_FAILED``, matching Phase 1's ``ValueError`` for a
  missing registry resolver. This tool does not (yet) accept a
  ``resolve_ref`` callable.
* When ``persist=True`` and ``slice_spec`` omits ``generated_at``, an
  ISO-8601 UTC timestamp is injected before serialization. The digest
  returned to the caller is computed from the *parsed* slice (which
  ignores ``generated_at``), so identical specs still yield identical
  digests across calls.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from opencode_arch.lifecycle_exec import paths
from opencode_arch.mcp.envelope import err, ok, resolve_repo, tool_result


@tool_result
async def slice_materialize_tool(
    repo_path: str,
    slice_spec: dict,
    persist: bool = True,
) -> dict:
    """Materialize a ModelSlice against the root package."""
    from pydantic import ValidationError

    from architecture_model.lifecycle.atomic_store import write_atomic
    from architecture_model.lifecycle.model_slice import (
        ModelSlice,
        compute_slice_digest,
    )
    from architecture_model.lifecycle.model_slice_materializer import materialize
    from architecture_model.lifecycle.package import load_package

    from opencode_arch.lifecycle_bridge import resolve_current_pkg

    # 1. Resolve repo.
    repo = resolve_repo(repo_path)

    # 2. Locate root package.
    tree = paths.ensure_all(repo)
    lifecycle_root: Path = tree["package_root"]
    pkg_yaml = lifecycle_root / "package.yaml"
    if not pkg_yaml.exists():
        return err("NOT_FOUND", "package.yaml not found")

    pkg = load_package(lifecycle_root)

    # Rebase pkg.root to CURRENT generation so materializer can locate the
    # published model at ``generations/<n>/model/.architecture-model.yaml``.
    pkg = resolve_current_pkg(pkg)

    # 3. Parse ModelSlice.
    if not isinstance(slice_spec, dict):
        return err(
            "SCHEMA_VIOLATION",
            "invalid slice spec",
            detail="slice_spec must be a mapping",
        )
    try:
        slice_obj = ModelSlice(**slice_spec)
    except ValidationError as exc:
        return err("SCHEMA_VIOLATION", "invalid slice spec", detail=str(exc))
    except (TypeError, ValueError) as exc:
        return err("SCHEMA_VIOLATION", "invalid slice spec", detail=str(exc))

    # 4. Federated scope not supported here.
    if slice_obj.scope == "federated":
        return err(
            "PRECONDITION_FAILED",
            "federated scope not supported without registry resolver",
        )

    # 5. Materialize.
    try:
        ms = materialize(slice_obj, pkg)
    except FileNotFoundError:
        return err("NOT_FOUND", "package model not found")

    # 6. Digest.
    digest = compute_slice_digest(slice_obj)

    # 7. Persist (optional).
    persisted_path: str | None = None
    if persist:
        spec_out = dict(slice_spec)
        if "generated_at" not in spec_out or spec_out.get("generated_at") is None:
            spec_out["generated_at"] = datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        slices_dir = lifecycle_root / "slices"
        slices_dir.mkdir(parents=True, exist_ok=True)
        target = slices_dir / f"{slice_obj.id}.yaml"
        write_atomic(
            target,
            yaml.safe_dump(spec_out, sort_keys=True).encode("utf-8"),
        )
        persisted_path = f"slices/{slice_obj.id}.yaml"

    return ok({
        "slice_id": ms.slice_id,
        "architecture_id": ms.architecture_id,
        "model_revision": ms.model_revision,
        "digest": digest,
        "stub_entity_ids": list(ms.stub_entity_ids),
        "warnings": [
            {"code": w.code, "message": w.message, "entity_id": w.entity_id}
            for w in ms.warnings
        ],
        "fragment": ms.model_fragment.to_dict(),
        "persisted_path": persisted_path,
    })
