"""arch_package_merge — native openAG three-way generation merge MCP tool.

Behavioral replacement for the legacy AMS architect_package_merge tool. Loads
three generation snapshots (base/local/remote) from the repo's GenerationStore,
runs openag.lifecycle.merge.three_way_merge, and — when conflict-free — records
the merged entity set as a NEW generation. When conflicts exist, nothing is
recorded and the conflict list is returned. openAG-shaped (generation
snapshots, not an AMS model+manifest bundle). No legacy AMS dependency.
"""
from __future__ import annotations

import re

from opencode_arch.mcp._arch_tool import arch_tool

_REV_RE = re.compile(r"^\d{7}$")


@arch_tool
async def arch_package_merge(
    repo_path: str = "",
    base_revision: str = "",
    local_revision: str = "",
    remote_revision: str = "",
) -> dict:
    """Three-way merge base/local/remote generation snapshots into a new generation."""
    from opencode_arch.mcp.envelope import err, resolve_repo

    resolve_repo(repo_path)

    for label, rev in (
        ("base", base_revision),
        ("local", local_revision),
        ("remote", remote_revision),
    ):
        if not isinstance(rev, str) or not _REV_RE.match(rev):
            raise ValueError(f"{label}_revision must be a 7-digit generation id")

    from openag.kernel.generations import GenerationStore
    from openag.lifecycle import store_root
    from openag.lifecycle.merge import three_way_merge

    store = GenerationStore(store_root(repo_path))
    snaps = {}
    for label, rev in (
        ("base", base_revision),
        ("local", local_revision),
        ("remote", remote_revision),
    ):
        gen = store.get(rev)
        if gen is None:
            return err("NOT_FOUND", f"generation {rev} not found", reason=f"{label}_revision_missing", revision=rev)
        snaps[label] = gen.get("entities") or []

    result = three_way_merge(snaps["base"], snaps["local"], snaps["remote"])

    if result["conflicts"]:
        return {
            "ok": True,
            "merged_generation": None,
            "conflicts": result["conflicts"],
            "stats": result["stats"],
        }

    merged_gen = store.record(
        result["merged"],
        reason=f"three-way-merge:{base_revision}+{local_revision}+{remote_revision}",
    )
    return {
        "ok": True,
        "merged_generation": merged_gen,
        "conflicts": [],
        "stats": result["stats"],
    }
