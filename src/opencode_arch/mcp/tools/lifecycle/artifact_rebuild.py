"""MCP tool: rebuild artifacts from ArtifactSpec/ViewSpec/ModelSlice inputs.

Thin envelope around :func:`opencode_arch.lifecycle_exec.rebuild.rebuild_artifacts`.

Envelope
--------
Success (even with per-artifact failures)::

    {"ok": True, "built": [...], "skipped": [...], "failed": [...],
     "journal_events": [...]}

Per the T12 plan, ``failed`` may be non-empty and the envelope still
reports ``ok: True`` — the tool "succeeds" as long as the rebuild
pipeline ran to completion. Individual artifact failures are surfaced
inside ``failed``.

Errors
------
* ``INVALID_ARGUMENT`` — non-list / empty ``artifact_specs``, non-list
  ``view_specs`` or ``slice_specs``, or non-bool ``force``.
* ``NOT_FOUND`` — ``repo_path`` does not exist.
* ``INTERNAL`` — unexpected exception (rebuild_artifacts is highly
  defensive; this should almost never fire).
"""
from __future__ import annotations

from opencode_arch.mcp.envelope import err, ok, resolve_repo, tool_result
from architecture_model.sil.decorators import instrumented


@instrumented("mcp_tool:architect_artifact_rebuild")
@tool_result
async def architect_artifact_rebuild_tool(
    repo_path: str,
    artifact_specs: list[dict],
    view_specs: list[dict],
    slice_specs: list[dict],
    force: bool = False,
) -> dict:
    """Execute the artifact rebuild pipeline. See module docstring."""
    # 1. Argument shape validation (before touching disk).
    if not isinstance(artifact_specs, list):
        return err("INVALID_ARGUMENT", "artifact_specs must be a list of dicts")
    if not artifact_specs:
        return err("INVALID_ARGUMENT", "artifact_specs must be non-empty")
    if not isinstance(view_specs, list):
        return err("INVALID_ARGUMENT", "view_specs must be a list of dicts")
    if not isinstance(slice_specs, list):
        return err("INVALID_ARGUMENT", "slice_specs must be a list of dicts")
    # bool is a subclass of int — check identity strictly.
    if not isinstance(force, bool):
        return err("INVALID_ARGUMENT", "force must be a bool")

    # 2. Path existence — resolve_repo raises FileNotFoundError → decorator
    #    maps that to NOT_FOUND. Do it explicitly so the executor's own
    #    ValueError (which would map to INVALID_ARGUMENT) never fires.
    resolve_repo(repo_path)

    # 3. Execute (importing lazily so import errors surface as INTERNAL).
    from opencode_arch.lifecycle_exec.rebuild import rebuild_artifacts

    report = rebuild_artifacts(
        repo_path,
        artifact_specs,
        view_specs,
        slice_specs,
        force=force,
    )
    return ok(report.to_dict())


__all__ = ["architect_artifact_rebuild_tool"]
