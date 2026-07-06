"""FastMCP server entry point for opencode-arch.

NOTE: The mcp package is not yet installed. This file is the intended
entry point once the mcp dependency is available. For now, the tools
are importable directly from opencode_arch.mcp.tools.
"""
from __future__ import annotations

# MCP server will be configured here once the mcp package is available.
# For Phase 1, tools are used directly via their async functions.

try:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("opencode-arch", description="Architecture extraction, generation, and validation tools")

    from opencode_arch.mcp.tools.extract import extract_architecture
    from opencode_arch.mcp.tools.validate import validate_architecture

    @mcp.tool()
    async def architect_extract(repo_path: str, focus: str = "all") -> str:
        """Extract architecture model from a repository."""
        return await extract_architecture(repo_path=repo_path, focus=focus)

    @mcp.tool()
    async def architect_validate(model_yaml: str, source_code: str = "", use_oracle: bool = False) -> dict:
        """Validate an architecture model for structural correctness."""
        return await validate_architecture(
            model_yaml=model_yaml,
            source_code=source_code or None,
            use_oracle=use_oracle,
        )

except ImportError:
    # mcp package not available - tools still work as standalone async functions
    mcp = None
