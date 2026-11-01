"""arch_observe — B-ROUND live-proprioception context-read MCP tool.

A PURE-READ tool returning RAW, filtered observation records from the repo's
journal (``<repo_path>/.architecture/observations.jsonl``). UNLIKE
``arch_health`` / ``arch_flags``, it does NOT load the openAG model/graph —
observations are model-independent, so a repo with no ``.architecture/model/``
dir but WITH observations still works.

NOTE: this tool is itself instrumented via ``@arch_tool`` (consistent
with every other ``arch_*`` tool, and philosophically correct for
self-proprioception). As a consequence it emits its OWN ``tool:arch_observe``
``tool_call`` observation at entry, which will then appear in a subsequent
UNFILTERED read.
"""
from __future__ import annotations

from opencode_arch.mcp.envelope import resolve_repo, tool_result
from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_observe(
    repo_path: str,
    component_id: str | None = None,
    io_kind: str | None = None,
    since: str | None = None,
) -> dict:
    """Return raw filtered runtime observation records (live proprioception)."""
    repo = resolve_repo(repo_path)

    from openag.observe import journal

    records = journal.read(repo)

    if component_id is not None:
        records = [r for r in records if r.get("component_id") == component_id]
    if io_kind is not None:
        records = [r for r in records if r.get("io_kind") == io_kind]
    if since is not None:
        records = [r for r in records if r.get("ts", "") >= since]

    return {"observations": records}
