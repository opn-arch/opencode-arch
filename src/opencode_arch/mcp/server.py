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
    from opencode_arch.mcp.tools.group import group_repository
    from opencode_arch.mcp.tools.check import check_representativeness
    from opencode_arch.mcp.tools.require import capture_requirement
    from opencode_arch.mcp.tools.feedback import record_feedback
    from opencode_arch.mcp.tools.ingest import ingest_source_graph

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

    @mcp.tool()
    async def architect_group(repo_path: str, target_groups: int = 0) -> dict:
        """Group repository modules into logical architecture components.

        Uses multi-signal affinity (subdirectory, name-prefix, imports) to
        suggest component boundaries. Call after scan, before extraction.

        Args:
            repo_path: Absolute path to the repository.
            target_groups: Desired number of groups (0 = auto-calculate).
        """
        return await group_repository(repo_path=repo_path, target_groups=target_groups)

    @mcp.tool()
    async def architect_check(repo_path: str, model_yaml: str) -> dict:
        """Verify model representativeness against code reality.

        Computes three sub-scores comparing model against AST-derived ground truth.
        Target: 100% on all three. Returns file_coverage, relationship_accuracy,
        boundary_coherence, and overall (0-100).
        """
        return await check_representativeness(repo_path=repo_path, model_yaml=model_yaml)

    @mcp.tool()
    async def architect_require(
        repo_path: str,
        requirement: str,
        component_id: str = "",
        priority: str = "must",
        context: str = "",
    ) -> dict:
        """Capture a functional requirement linked to an architecture component.

        Stores requirements in .architecture/requirements.yaml with MoSCoW priority.

        Args:
            repo_path: Absolute path to the repository.
            requirement: The requirement text.
            component_id: Component ID (e.g., "COMP-3"). Empty string = unlinked.
            priority: must | should | could (MoSCoW).
            context: Additional context from conversation.
        """
        return await capture_requirement(
            repo_path=repo_path,
            requirement=requirement,
            component_id=component_id or None,
            priority=priority,
            context=context,
        )

    @mcp.tool()
    async def architect_feedback(
        repo_path: str,
        feedback_type: str,
        content: str,
        context: dict | None = None,
        rating: int | None = None,
        correction: dict | None = None,
    ) -> dict:
        """Record user feedback for model improvement and training.

        Appends feedback to .architecture/feedback.jsonl for future training use.

        Args:
            repo_path: Absolute path to the repository.
            feedback_type: "correction" | "rating" | "tool_feedback" | "training".
            content: The feedback content (human-readable).
            context: Optional context dict.
            rating: Optional 1-5 quality rating.
            correction: Optional structured correction {entity_id, field, old, new}.
        """
        return await record_feedback(
            repo_path=repo_path,
            feedback_type=feedback_type,
            content=content,
            context=context,
            rating=rating,
            correction=correction,
        )

    @mcp.tool()
    async def architect_ingest(repo_path: str, source_graph_json: str) -> dict:
        """Ingest a SourceGraph JSON for any language repository.

        Accepts dependency and export data (from external tools or agent analysis),
        groups modules into components, extracts interface contracts, and stores
        the architecture model.

        Args:
            repo_path: Absolute path to the repository.
            source_graph_json: JSON string with SourceGraph data. Format:
                {"language": "typescript", "units": [{"file": "...", "exports": [...]}], "edges": [...]}
        """
        return await ingest_source_graph(repo_path=repo_path, source_graph_json=source_graph_json)

except ImportError:
    # mcp package not available - tools still work as standalone async functions
    mcp = None


if __name__ == "__main__":
    if mcp is not None:
        mcp.run()
    else:
        print("Error: mcp package not installed. Install with: pip install 'opencode-arch[mcp]'")
        raise SystemExit(1)
