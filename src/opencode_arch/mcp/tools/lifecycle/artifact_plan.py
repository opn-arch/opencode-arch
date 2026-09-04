"""MCP tool: build a rebuild plan (DAG) from a list of ArtifactSpec dicts.

Pure planning — does not touch the lifecycle filesystem beyond validating
that ``repo_path`` exists (for envelope consistency with sibling tools).

Envelope
--------
Success::

    {"ok": True, "plan": {
        "nodes": [{"spec_id": str, "depends_on": [str, ...]}, ...],
        "order": [str, ...],
    }}

``nodes`` is sorted by ``spec_id``; each ``depends_on`` is the sorted
list of upstream spec ids (i.e. inbound edges — a zip's ``bundle_refs``).
``order`` is :meth:`ArtifactDAG.topological_order` output.

Errors
------
* ``INVALID_ARGUMENT`` — empty ``artifact_specs``, non-list input,
  malformed spec dict, or duplicate spec ids.
* ``PRECONDITION_FAILED`` — DAG cycle (``ArtifactDAGCycle``) or a
  ``bundle_refs`` entry that names an unknown artifact
  (``MissingArtifactRef``); the offending nodes/ref are surfaced in
  ``error.details``.
"""
from __future__ import annotations

from opencode_arch.mcp.envelope import err, ok, resolve_repo, tool_result


@tool_result
async def artifact_plan_tool(
    repo_path: str,
    artifact_specs: list[dict],
) -> dict:
    """Return the topological rebuild plan for ``artifact_specs``."""
    from pydantic import ValidationError

    from architecture_model.lifecycle.artifact_dag import (
        ArtifactDAGCycle,
        MissingArtifactRef,
        build_artifact_dag,
    )
    from architecture_model.lifecycle.artifact_spec import ArtifactSpec

    # 1. Existence check (repo_path is not otherwise used by this tool).
    resolve_repo(repo_path)

    # 2. Shape / emptiness.
    if not isinstance(artifact_specs, list):
        return err(
            "INVALID_ARGUMENT",
            "artifact_specs must be a list of dicts",
        )
    if not artifact_specs:
        return err("INVALID_ARGUMENT", "artifact_specs must be non-empty")

    # 3. Parse each dict into ArtifactSpec.
    parsed: list[ArtifactSpec] = []
    for idx, raw in enumerate(artifact_specs):
        if not isinstance(raw, dict):
            return err(
                "INVALID_ARGUMENT",
                f"artifact_specs[{idx}] must be a mapping",
            )
        try:
            parsed.append(ArtifactSpec(**raw))
        except ValidationError as exc:
            return err(
                "INVALID_ARGUMENT",
                f"artifact_specs[{idx}] failed to parse",
                detail=str(exc),
            )
        except (TypeError, ValueError) as exc:
            return err(
                "INVALID_ARGUMENT",
                f"artifact_specs[{idx}] failed to parse",
                detail=str(exc),
            )

    # 4. Reject duplicate ids explicitly — build_artifact_dag would silently
    #    coalesce them via dict overwrite.
    seen: set[str] = set()
    duplicates: list[str] = []
    for spec in parsed:
        if spec.id in seen:
            duplicates.append(spec.id)
        seen.add(spec.id)
    if duplicates:
        return err(
            "INVALID_ARGUMENT",
            "duplicate artifact spec ids",
            duplicates=sorted(set(duplicates)),
        )

    # 5. Build DAG (raises MissingArtifactRef / ArtifactDAGCycle).
    try:
        dag = build_artifact_dag(parsed)
    except MissingArtifactRef as exc:
        return err(
            "PRECONDITION_FAILED",
            "artifact_specs references an unknown artifact id",
            detail=str(exc),
        )
    except ArtifactDAGCycle as exc:
        # Message shape: "cycle detected among artifacts: ['a', 'b']"
        return err(
            "PRECONDITION_FAILED",
            "artifact DAG contains a cycle",
            detail=str(exc),
        )

    # 6. Topological order (deterministic Kahn's).
    order = dag.topological_order()

    # 7. Assemble nodes with sorted depends_on (inbound edges = upstreams).
    #    For non-zip specs, bundle_refs is None/empty → depends_on == [].
    depends_by_id: dict[str, list[str]] = {}
    for spec in parsed:
        if spec.renderer == "zip" and spec.bundle_refs:
            depends_by_id[spec.id] = sorted(spec.bundle_refs)
        else:
            depends_by_id[spec.id] = []

    nodes = [
        {"spec_id": sid, "depends_on": depends_by_id[sid]}
        for sid in sorted(depends_by_id)
    ]

    return ok({"plan": {"nodes": nodes, "order": order}})


__all__ = ["artifact_plan_tool"]
