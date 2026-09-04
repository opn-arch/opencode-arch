"""MCP tool: render a projected view to bytes via a named renderer.

Combines projection (via the shared helper) with the renderer registry
from ``architecture_model.lifecycle.renderers``. Returns UTF-8 body,
content type, and a sha256 digest of the raw bytes.

Deviations
----------
* ``renderer == "zip"`` is rejected at the tool boundary
  (``PRECONDITION_FAILED``). The ``render_zip`` implementation requires
  a ``resolve_artifact`` callable which is not part of this API.
* Only text-shaped renderers are supported: ``svg``, ``markdown``,
  ``html``, ``ai-context``. All bytes are UTF-8-decodable. ``body_base64``
  is reserved for future binary renderers and returned as ``None``.
"""
from __future__ import annotations

import hashlib

from opencode_arch.mcp.envelope import err, ok, tool_result
from opencode_arch.mcp.tools.lifecycle._view_common import load_and_materialize


_CONTENT_TYPES = {
    "svg": "image/svg+xml",
    "markdown": "text/markdown",
    "html": "text/html",
    "ai-context": "text/plain",
}


@tool_result
async def view_render_tool(
    repo_path: str,
    view_spec: dict,
    slice_id: str,
    artifact_spec: dict,
) -> dict:
    """Project ``view_spec`` and render it via ``artifact_spec.renderer``."""
    from pydantic import ValidationError

    from architecture_model.lifecycle.artifact_spec import ArtifactSpec
    from architecture_model.lifecycle.renderers import get_renderer
    from architecture_model.lifecycle.view_projection import (
        ProjectorNotFound,
        SliceMismatch,
        project,
    )
    from architecture_model.lifecycle.view_spec import ViewSpec

    # Steps 1–6.
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

    # 9. Parse ArtifactSpec.
    if not isinstance(artifact_spec, dict):
        return err(
            "SCHEMA_VIOLATION",
            "invalid artifact spec",
            detail="artifact_spec must be a mapping",
        )
    try:
        artifact = ArtifactSpec(**artifact_spec)
    except ValidationError as exc:
        return err("SCHEMA_VIOLATION", "invalid artifact spec", detail=str(exc))
    except (TypeError, ValueError) as exc:
        return err("SCHEMA_VIOLATION", "invalid artifact spec", detail=str(exc))

    # 10. Reject zip renderer at tool boundary.
    if artifact.renderer == "zip":
        return err(
            "PRECONDITION_FAILED",
            "zip renderer requires bundle resolver, not yet supported",
        )

    # 11. Look up renderer.
    try:
        renderer = get_renderer(artifact.renderer)
    except KeyError:
        return err(
            "NOT_FOUND",
            "renderer not registered",
            renderer=artifact.renderer,
        )

    # 12. Render.
    try:
        body_bytes = renderer(pv, artifact)
    except ValueError as exc:
        return err(
            "SCHEMA_VIOLATION",
            "renderer rejected artifact",
            detail=str(exc),
        )

    # 13. Digest.
    digest = hashlib.sha256(body_bytes).hexdigest()

    # 14-15. Body.
    content_type = _CONTENT_TYPES.get(artifact.renderer, "application/octet-stream")
    body_utf8 = body_bytes.decode("utf-8")

    return ok({
        "artifact_id": artifact.id,
        "content_type": content_type,
        "body_utf8": body_utf8,
        "body_base64": None,
        "digest": digest,
        "warnings": list(pv.warnings),
    })


__all__ = ["view_render_tool"]
