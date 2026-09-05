"""MCP tool: project a ViewSpec over a persisted, materialized ModelSlice.

Loads the slice from disk (previously persisted by
``architect_slice_materialize``), materializes it against the CURRENT
package, then projects the caller-supplied ``ViewSpec`` via
``architecture_model.lifecycle.view_projection.project``.

Deviations
----------
* Only the ``DEFAULT_REGISTRY`` is consulted. Callers cannot supply
  their own registry through this tool boundary (Phase 2 scope).
"""
from __future__ import annotations

from opencode_arch.mcp.envelope import err, ok, tool_result
from opencode_arch.mcp.tools.lifecycle._view_common import load_and_materialize


@tool_result
async def view_project_tool(
    repo_path: str,
    view_spec: dict,
    slice_id: str,
) -> dict:
    """Project a ViewSpec over the persisted slice ``slice_id``."""
    from pydantic import ValidationError

    from architecture_model.lifecycle.view_projection import (
        ProjectorNotFound,
        SliceMismatch,
        project,
    )
    from architecture_model.lifecycle.view_spec import ViewSpec

    # Steps 1–6: shared helper.
    result = await load_and_materialize(repo_path, slice_id)
    if isinstance(result, dict):
        return result
    ms, _ = result

    # 7. Parse ViewSpec.
    if not isinstance(view_spec, dict):
        return err(
            "SCHEMA_VIOLATION",
            "invalid view spec",
            detail="view_spec must be a mapping",
        )
    try:
        view = ViewSpec(**view_spec)
    except ValidationError as exc:
        return err("SCHEMA_VIOLATION", "invalid view spec", detail=str(exc))
    except (TypeError, ValueError) as exc:
        return err("SCHEMA_VIOLATION", "invalid view spec", detail=str(exc))

    # 8. Project.
    try:
        pv = project(view, ms)
    except ProjectorNotFound:
        return err(
            "NOT_FOUND",
            "projector not registered",
            projector=view.projector,
        )
    except SliceMismatch as exc:
        return err(
            "PRECONDITION_FAILED",
            "slice_ref does not match materialized slice",
            detail=str(exc),
        )

    # 9. Serialize (DiagramSpec is a dataclass with .to_dict()).
    return ok({
        "view_id": pv.view_id,
        "slice_id": pv.slice_id,
        "model_revision": pv.model_revision,
        "diagram_spec": pv.diagram_spec.to_dict(),
        "provenance": pv.provenance,
        "warnings": list(pv.warnings),
    })


__all__ = ["view_project_tool"]
