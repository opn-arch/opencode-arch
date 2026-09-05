"""Shared helpers for lifecycle view tools (T9).

Contract
--------
:func:`load_and_materialize` performs steps 1–6 shared between
``view_project`` and ``view_render``:

1. Resolve repo.
2. Locate lifecycle root; verify ``package.yaml`` exists.
3. Load persisted slice from ``<lifecycle>/slices/<slice_id>.yaml``.
4. Parse into ``ModelSlice`` (rejecting federated scope).
5. Load + rebase root package to CURRENT generation.
6. Materialize the slice against the current model.

Return contract
---------------
Returns a 2-tuple ``(materialized_slice, None)`` on success (the second
slot is reserved for future warnings).

Returns an **error envelope dict** (``{"ok": False, "error": {...}}``)
on any failure. Callers MUST branch on ``isinstance(result, tuple)``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from opencode_arch.lifecycle_exec import paths
from opencode_arch.mcp.envelope import err, resolve_repo


async def load_and_materialize(
    repo_path: str,
    slice_id: str,
) -> tuple[Any, None] | dict:
    """Load persisted slice + materialize against current package.

    Returns ``(MaterializedSlice, None)`` on success, or an error
    envelope dict on failure.
    """
    from pydantic import ValidationError

    from architecture_model.lifecycle.model_slice import ModelSlice
    from architecture_model.lifecycle.model_slice_materializer import materialize
    from architecture_model.lifecycle.package import load_package

    from opencode_arch.lifecycle_bridge import resolve_current_pkg

    # 1. Resolve repo (may raise FileNotFoundError → caught by @tool_result).
    repo = resolve_repo(repo_path)

    # 2. Locate root package.
    tree = paths.ensure_all(repo)
    lifecycle_root: Path = tree["package_root"]
    if not (lifecycle_root / "package.yaml").exists():
        return err("NOT_FOUND", "package.yaml not found")

    # 3. Load persisted slice.
    slice_path = lifecycle_root / "slices" / f"{slice_id}.yaml"
    if not slice_path.exists():
        return err("NOT_FOUND", "slice not found", slice_id=slice_id)
    try:
        loaded = yaml.safe_load(slice_path.read_text()) or {}
    except yaml.YAMLError as exc:
        return err(
            "SCHEMA_VIOLATION",
            "invalid persisted slice",
            detail=str(exc),
        )
    if not isinstance(loaded, dict):
        return err(
            "SCHEMA_VIOLATION",
            "invalid persisted slice",
            detail="slice yaml must be a mapping",
        )

    # 4. Parse ModelSlice.
    try:
        slice_obj = ModelSlice(**loaded)
    except ValidationError as exc:
        return err("SCHEMA_VIOLATION", "invalid persisted slice", detail=str(exc))
    except (TypeError, ValueError) as exc:
        return err("SCHEMA_VIOLATION", "invalid persisted slice", detail=str(exc))

    if slice_obj.scope == "federated":
        return err(
            "PRECONDITION_FAILED",
            "federated scope not supported without registry resolver",
        )

    # 5. Load + rebase package to CURRENT generation.
    pkg = resolve_current_pkg(load_package(lifecycle_root))

    # 6. Materialize.
    try:
        ms = materialize(slice_obj, pkg)
    except FileNotFoundError:
        return err("NOT_FOUND", "package model not found")

    return (ms, None)


__all__ = ["load_and_materialize"]
