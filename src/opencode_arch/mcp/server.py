# src/opencode_arch/mcp/server.py
"""FastMCP server entry point for opencode-arch.

Run with: python -m opencode_arch.mcp.server
"""
from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        "opencode-arch",
        instructions="Architecture context compression, validation, and code quality tools",
    )

    from opencode_arch.mcp.tools.scan import scan_repository
    from opencode_arch.mcp.tools.slice import slice_context
    from opencode_arch.mcp.tools.validate import validate_architecture
    from opencode_arch.mcp.tools.extract import store_extraction
    from opencode_arch.mcp.tools.generate import run_tests_on_generated_code

    @mcp.tool()
    async def architect_scan(repo_path: str) -> dict:
        """Scan a repository to generate its reality manifest (AST analysis).

        Returns a manifest with: modules, functions, classes, imports, metrics.
        Use this as raw material before slicing context.
        """
        return await scan_repository(repo_path=repo_path)

    @mcp.tool()
    async def architect_slice(repo_path: str, focus: str = "all", budget: int = 4000, detail: str = "standard") -> str:
        """Generate an optimized context slice from a repository.

        Compresses the full repository into a dense context string within the
        token budget. This is the core token-arbitrage function.

        Args:
            repo_path: Absolute path to the repository.
            focus: "all", an F-block ID ("F1"), layer name, or artifact name ("icd").
            budget: Maximum token budget (default 4000).
            detail: "minimal", "standard", or "full".
        """
        return await slice_context(repo_path=repo_path, focus=focus, budget=budget, detail=detail)

    @mcp.tool()
    async def architect_validate(model_yaml: str) -> dict:
        """Validate an architecture model for structural correctness.

        Checks: ID uniqueness, referential integrity, orphan detection,
        capability realization, meta completeness. Returns score 0-100.
        """
        return await validate_architecture(model_yaml=model_yaml)

    @mcp.tool()
    async def architect_extract(repo_path: str, model_yaml: str, context_tokens: int = 0) -> dict:
        """Store a validated architecture extraction.

        Call AFTER the agent produces a YAML model. Validates, writes to
        .architecture-model.yaml, and records telemetry.
        """
        return await store_extraction(repo_path=repo_path, model_yaml=model_yaml, context_tokens=context_tokens)

    @mcp.tool()
    async def architect_generate(repo_path: str, test_command: str = "") -> dict:
        """Run tests on generated code to verify quality.

        Executes the repository's test suite against generated code.
        Returns pass rate, failures, and total test count.
        """
        return await run_tests_on_generated_code(repo_path=repo_path, test_command=test_command or None)

except ImportError:
    # mcp package not available - tools still work as standalone async functions
    mcp = None


if __name__ == "__main__":
    if mcp is not None:
        mcp.run()
    else:
        print("Error: mcp package not installed. Install with: pip install 'opencode-arch[mcp]'")
        raise SystemExit(1)
