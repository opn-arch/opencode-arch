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
    from opencode_arch.mcp.tools.stats import get_stats
    from opencode_arch.mcp.tools.correct import store_correction
    from opencode_arch.mcp.tools.docs import generate_docs
    from opencode_arch.mcp.tools.decompose import decompose_repository
    from opencode_arch.mcp.tools.export import export_repository
    from opencode_arch.mcp.tools.llm_audit import run_llm_audit
    from opencode_arch.mcp.tools.trace_requirements import trace_requirements
    from opencode_arch.mcp.tools.author import author_architecture
    from opencode_arch.mcp.tools.gate import check_gate

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

    @mcp.tool()
    async def architect_stats(repo_path: str = "", tool_filter: str = "") -> dict:
        """Aggregate session and historical quality metrics.

        Returns session stats, historical telemetry summary, and actionable suggestions.

        Args:
            repo_path: Optional - filter stats to specific repo.
            tool_filter: Optional - filter to specific tool name.
        """
        return await get_stats(repo_path=repo_path, tool_filter=tool_filter)

    @mcp.tool()
    async def architect_correct(
        repo_path: str,
        correction_type: str,
        target: str,
        reason: str,
        suggestion: dict | None = None,
    ) -> dict:
        """Store a structured correction for the architecture model.

        Corrections are consumed on next pipeline run to improve the model.

        Args:
            repo_path: Absolute path to the repository.
            correction_type: split_component | merge_components | add_component |
                remove_component | add_relationship | remove_relationship | rename | reclassify.
            target: Entity ID being corrected (e.g., "COMP-3").
            reason: Why this correction is needed.
            suggestion: Optional structured suggestion dict.
        """
        return await store_correction(
            repo_path=repo_path,
            correction_type=correction_type,
            target=target,
            reason=reason,
            suggestion=suggestion,
        )

    @mcp.tool()
    async def architect_docs(repo_path: str, formats: str = "all") -> dict:
        """Generate standard SE documentation from architecture model.

        Produces component specs, ICDs, dependency matrix, health report from
        .architecture-model.yaml. Run after extraction.

        Args:
            repo_path: Absolute path to the repository.
            formats: Comma-separated doc types: all, component_spec, icd,
                dependency_matrix, health, drift, index.
        """
        return await generate_docs(repo_path=repo_path, formats=formats)

    @mcp.tool()
    async def architect_decompose(repo_path: str) -> dict:
        """Decompose architecture model into per-block sub-models and recursive manifests.

        Reads .architecture-model.yaml, traces relationships per F-block,
        writes sub-models to .architecture-models/ and per-block manifests to
        .architecture/manifests/. Run after extraction.

        Args:
            repo_path: Absolute path to the repository.
        """
        return await decompose_repository(repo_path=repo_path)

    @mcp.tool()
    async def architect_export(
        repo_path: str,
        output_dir: str = "",
        output_format: str = "dir",
        prefix: str = "",
    ) -> dict:
        """Export repository architecture as flat files for mobile AI.

        Builds a set of flat files (model, sub-models, docs, manifests, specs,
        diagrams, skills, reference docs) for use in token-limited AI environments.

        Args:
            repo_path: Absolute path to the repository.
            output_dir: Where to write output. Default: {repo_path}/.architecture-export/
            output_format: "dir" (flat directory) or "zip" (single zip file).
            prefix: File prefix override. Default: auto-derived from repo name.
        """
        return await export_repository(
            repo_path=repo_path,
            output_dir=output_dir,
            output_format=output_format,
            prefix=prefix,
        )

    @mcp.tool()
    async def architect_llm_audit(repo_path: str, model_yaml: str = "") -> dict:
        """Run two-stage LLM functional-decomposition audit.

        Independent second opinion on F-block boundaries. Compares blind LLM
        decomposition against tool's assignment + quality metrics.
        Flag-gated: never auto-invoked.

        Args:
            repo_path: Absolute path to the repository.
            model_yaml: Optional model YAML. If empty, reads .architecture-model.yaml.
        """
        return await run_llm_audit(repo_path=repo_path, model_yaml=model_yaml)

    @mcp.tool()
    async def architect_trace_requirements(
        repo_path: str,
        model_yaml: str = "",
        requirements_doc: str = "",
    ) -> dict:
        """Trace requirements to functions.

        If requirements_doc provided: parse structurally, fall back to LLM for freeform.
        If no requirements_doc: use retroactive derivation from model.
        Then match functions to requirements.
        Output: .architecture-models/requirements-trace.json

        Args:
            repo_path: Absolute path to the repository.
            model_yaml: Optional model YAML. If empty, reads .architecture-model.yaml.
            requirements_doc: Optional path to requirements document.
        """
        return await trace_requirements(
            repo_path=repo_path,
            model_yaml=model_yaml,
            requirements_doc=requirements_doc,
        )

    @mcp.tool()
    async def architect_author(repo_path: str, requirements_text: str) -> dict:
        """Forward-author an architecture model from requirements text.

        Parses requirements (actors, capabilities, constraints) and produces
        a concept-phase .architecture-model.yaml. Use before code exists.

        Args:
            repo_path: Absolute path to the repository root.
            requirements_text: Free-form or structured requirements document.
        """
        return await author_architecture(repo_path=repo_path, requirements_text=requirements_text)

    @mcp.tool()
    async def architect_gate(repo_path: str, model_yaml: str = "") -> dict:
        """Check development gate readiness for an architecture model.

        Evaluates capability realization, constraint allocation, and file coverage
        against code reality. Returns phase_requirements_met boolean.

        Args:
            repo_path: Absolute path to the repository root.
            model_yaml: Optional model YAML. If empty, reads .architecture-model.yaml.
        """
        return await check_gate(repo_path=repo_path, model_yaml=model_yaml)

except ImportError:
    # mcp package not available - tools still work as standalone async functions
    mcp = None


if __name__ == "__main__":
    if mcp is not None:
        mcp.run()
    else:
        print("Error: mcp package not installed. Install with: pip install 'opencode-arch[mcp]'")
        raise SystemExit(1)
