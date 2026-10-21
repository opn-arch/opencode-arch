"""Runtime registration guard: the FastMCP server must actually build.

Unlike ``test_round_surface_registered.py`` — which falls back to a
source-grep of ``server.py`` when FastMCP is missing and therefore passes
even when ``server.mcp is None`` — this test asserts the *runtime* object
exists. It red-guards the silent ``except ImportError`` at the bottom of
``server.py`` that nulls ``mcp`` when the installed ``mcp`` distribution
lacks ``mcp.server.fastmcp`` (e.g. the conflicting ``mcp>=2`` package).

It fails loudly if the official MCP SDK (``mcp>=1.0,<2``) is not the one
installed, which is the only configuration in which the server can serve
tools at all.
"""
import asyncio

EXPECTED_ARCH_TOOLS = {
    "arch_frontier",
    "arch_owed",
    "arch_gaps",
    "arch_slice",
    "arch_health",
    "arch_flags",
    "arch_observe",
    "arch_ingest_telemetry",
    "arch_history",
    "arch_lessons",
    "arch_round",
}


def test_server_mcp_object_is_built():
    """The FastMCP instance must be non-None (SDK import succeeded)."""
    from opencode_arch.mcp import server

    assert server.mcp is not None, (
        "server.mcp is None — the official MCP SDK (mcp>=1.0,<2) is not "
        "installed. server.py:13 'from mcp.server.fastmcp import FastMCP' "
        "failed and the silent 'except ImportError' nulled mcp, so ZERO "
        "tools register at runtime."
    )


def test_eleven_arch_tools_register_at_runtime():
    """All eleven B-ROUND arch_* tools must be live on the running server."""
    from opencode_arch.mcp import server

    assert server.mcp is not None, "server.mcp is None (SDK not installed)"

    tools = asyncio.run(server.mcp.list_tools())
    names = {t.name for t in tools}

    missing = EXPECTED_ARCH_TOOLS - names
    assert not missing, f"arch_* tools not registered at runtime: {sorted(missing)}"
