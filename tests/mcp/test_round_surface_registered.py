"""Assert the eleven B-ROUND round-centric G1–G5 MCP tools are registered.

Dual-path introspection mirroring
``tests/integration/test_mcp_lifecycle.py::test_all_phase2_mcp_tools_registered``:
when FastMCP is importable, introspect ``mcp._tool_manager``; otherwise
source-grep ``server.py`` for ``@mcp.tool()`` + ``async def arch_<name>(``
decorator pairs. FastMCP is NOT installed in the test env, so the grep
path is what actually runs.
"""
import re
from pathlib import Path

EXPECTED = {
    "arch_frontier", "arch_owed", "arch_gaps", "arch_slice",
    "arch_round",
    "arch_propose_cut", "arch_score_cut", "arch_allocate_contract",
    "arch_integrate",
    "arch_bind", "arch_commit_generation",
}


def test_round_surface_registered():
    from opencode_arch.mcp import server

    if server.mcp is not None:
        tm = server.mcp._tool_manager
        registered = set(getattr(tm, "_tools", {}).keys()) or set(
            getattr(tm, "tools", {}).keys()
        )
    else:
        src = Path(server.__file__).read_text(encoding="utf-8")
        pat = re.compile(
            r"@mcp\.tool\([^)]*\)\s*(?:@[^\n]+\n\s*)*"
            r"async\s+def\s+(arch_[A-Za-z_0-9]+)\s*\(",
        )
        registered = set(pat.findall(src))

    missing = EXPECTED - registered
    assert not missing, f"unregistered round tools: {sorted(missing)}"
