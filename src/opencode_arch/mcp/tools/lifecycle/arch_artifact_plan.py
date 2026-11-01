"""arch_artifact_plan — native openAG artifact DAG planning MCP tool.

Behavioral replacement for the legacy AMS architect_artifact_plan tool. Builds
a deterministic topological rebuild plan from a list of artifact specs via
openag.lifecycle.artifacts.plan_artifacts. Pure planning — no filesystem beyond
an existence check on repo_path. No legacy AMS dependency.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_artifact_plan(
    repo_path: str = "",
    artifact_specs: list[dict] | None = None,
) -> dict:
    """Return the deterministic topological rebuild plan for artifact_specs."""
    from opencode_arch.mcp.envelope import err, resolve_repo

    resolve_repo(repo_path)

    if artifact_specs is None:
        artifact_specs = []

    from openag.lifecycle.artifacts import (
        ArtifactCycle,
        UnknownRef,
        plan_artifacts,
    )

    try:
        plan = plan_artifacts(artifact_specs)
    except (ArtifactCycle, UnknownRef) as exc:
        return err("PRECONDITION_FAILED", str(exc))

    return {"ok": True, "plan": plan}
