"""arch_scan — native scan-report MCP tool over the openAG ground graph.

Behavioral replacement for the legacy AMS ``architect_scan`` manifest tool.
Produces a deterministic module / import-edge inventory of the repo's source
tree via :func:`openag.graph.scan_report.scan_report` (AST-only, no code
executed, no legacy AMS dependency).

Scans ``<repo_path>/src`` when present, else the repo root itself.
"""

from __future__ import annotations

from opencode_arch.mcp.envelope import resolve_repo
from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_scan(repo_path: str, mode: str = "full") -> dict:
    """Return the module / import-edge inventory of the repo's source tree."""
    resolved = resolve_repo(repo_path)

    from openag.graph.scan_report import scan_report

    src_root = resolved / "src"
    if not src_root.is_dir():
        src_root = resolved

    return scan_report(src_root)
