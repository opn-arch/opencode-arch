# src/opencode_arch/mcp/server.py
"""FastMCP server entry point for opencode-arch.

Run with: python -m opencode_arch.mcp.server
"""

from __future__ import annotations

import json
from pathlib import Path

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
    from opencode_arch.mcp.tools.pipeline import run_pipeline
    from opencode_arch.mcp.tools.learn import record_learning, GLOBAL_LEARNING_PATH

    @mcp.tool()
    async def architect_scan(repo_path: str) -> dict:
        """Scan a repository to understand its structure. ALWAYS call this FIRST when exploring any unfamiliar codebase.

        ALWAYS call this instead of reading files individually when you need to understand a project's structure.
        If you are about to use grep/glob/find to explore a repo, STOP and call architect_scan instead.
        Returns a manifest with: modules, functions, classes, imports, metrics.
        """
        return await scan_repository(repo_path=repo_path)

    @mcp.tool()
    async def architect_slice(
        repo_path: str, focus: str = "all", budget: int = 4000, detail: str = "standard"
    ) -> str:
        """ALWAYS call this before implementing features to get relevant architectural context.

        If you find yourself reading more than 3 files manually, STOP and call architect_slice instead.
        This compresses the full repository into a dense context string within the token budget —
        one call replaces 10+ file reads. MUST be your first step when working on any feature or bug.

        Args:
            repo_path: Absolute path to the repository.
            focus: "all", an F-block ID ("F1"), layer name, or artifact name.
                Available artifact modes for focused views:
                - "icd" — interface control document (APIs, protocols)
                - "use-cases" — actor-driven use case analysis
                - "requirements-analysis" — capabilities, constraints, quality attributes
                - "functional-architecture" — actors, capabilities, behaviors
                - "logical-architecture" — components, layers, allocation
                - "conops" — concept of operations
                - "testing" — test-relevant capabilities and components
                - "operations-manual" — operational behaviors and interfaces
                - "deployment-guide" — deployment topology and resources
                - "data-dictionary" — data models and schemas
                - "readme" — high-level project overview
            budget: Maximum token budget (default 4000).
            detail: "minimal", "standard", or "full".
        """
        return await slice_context(repo_path=repo_path, focus=focus, budget=budget, detail=detail)

    @mcp.tool()
    async def architect_validate(model_yaml: str = "", repo_path: str = "") -> dict:
        """Validate an architecture model for structural correctness.

        Checks: ID uniqueness, referential integrity, orphan detection,
        capability realization, meta completeness. Returns score 0-100.

        If model_yaml is empty and repo_path is provided, reads from .architecture-model.yaml.
        """
        return await validate_architecture(model_yaml=model_yaml, repo_path=repo_path)

    @mcp.tool()
    async def architect_extract(repo_path: str, model_yaml: str, context_tokens: int = 0) -> dict:
        """Store a validated architecture extraction.

        Call AFTER the agent produces a YAML model. Validates, writes to
        .architecture-model.yaml, and records telemetry.
        """
        return await store_extraction(
            repo_path=repo_path, model_yaml=model_yaml, context_tokens=context_tokens
        )

    @mcp.tool()
    async def architect_generate(repo_path: str, test_command: str = "") -> dict:
        """Run tests on generated code to verify quality.

        Executes the repository's test suite against generated code.
        Returns pass rate, failures, and total test count.
        """
        return await run_tests_on_generated_code(
            repo_path=repo_path, test_command=test_command or None
        )

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
    async def architect_check(repo_path: str, model_yaml: str = "") -> dict:
        """Verify model representativeness against code reality.

        Computes three sub-scores comparing model against AST-derived ground truth.
        Target: 100% on all three. Returns file_coverage, relationship_accuracy,
        boundary_coherence, and overall (0-100).

        If model_yaml is empty, reads from {repo_path}/.architecture-model.yaml.
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
        """Call whenever a user states or implies a requirement. If the user says 'I want...', 'it should...', 'we need...', capture it here immediately.

        MUST be called the moment a requirement is identified — do not wait. Every user intent
        that describes desired behavior, constraint, or capability MUST be recorded here.
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
    async def architect_log(
        repo_path: str,
        log_type: str,
        title: str,
        content: str = "",
        context: dict | None = None,
    ) -> str:
        """Call after EVERY significant decision, task completion, or issue discovery.

        If you just made a choice between alternatives, call this. If you just finished a task, call this.
        If you discovered a bug or issue, call this. NEVER let a decision or milestone pass without logging it.
        This is your structured memory — without it, context is lost between sessions.

        Args:
            repo_path: Absolute path to the repository.
            log_type: "decision" | "progress" | "observation" | "issue" | "requirement"
            title: Short title (1 line).
            content: Optional longer description.
            context: Optional context dict {files_changed, component_id, tool, rationale}.
        """
        from .tools.log import log_entry

        result = await log_entry(repo_path, log_type, title, content, context)
        return json.dumps(result, indent=2)

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

        Produces component specs, ICDs, dependency matrix, health report,
        and SE documents (ConOps, Functional Analysis, Logical Architecture,
        Requirements Analysis, V&V, Operations Manual, Maintenance Manual,
        Use Cases, Risk Assessment, Interface Specification, Artifact
        Traceability Map) from .architecture-model.yaml. Run after extraction.

        Args:
            repo_path: Absolute path to the repository.
            formats: Comma-separated doc types: all, component_spec, icd,
                dependency_matrix, health, drift, index, se_all, conops,
                functional_analysis, logical_architecture, requirements_analysis,
                verification_validation, operations_manual, maintenance_manual,
                use_cases, risk_assessment, interface_spec, artifact_traceability.
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
    async def architect_diff(
        repo_path: str,
        model_a_yaml: str = "",
        model_b_yaml: str = "",
    ) -> str:
        """Compare two architecture model versions and return a structured diff.

        If model_a_yaml is empty, reads the current .architecture-model.yaml.
        If model_b_yaml is empty, reads the last git-committed version.

        Returns added/removed/changed components and relationships.

        Args:
            repo_path: Absolute path to the repository.
            model_a_yaml: Current model YAML (empty = read from disk).
            model_b_yaml: Previous model YAML (empty = read from git HEAD).
        """
        from opencode_arch.mcp.tools.diff import diff_models

        return await diff_models(
            repo_path=repo_path,
            model_a_yaml=model_a_yaml,
            model_b_yaml=model_b_yaml,
        )

    @mcp.tool()
    async def architect_gate(repo_path: str, model_yaml: str = "") -> dict:
        """ALWAYS call before marking any task, feature, or PR as complete.

        This validates that architecture constraints are satisfied. MUST be your final check
        before claiming work is done. If this returns phase_requirements_met=false, the work is NOT complete.

        Args:
            repo_path: Absolute path to the repository root.
            model_yaml: Optional model YAML. If empty, reads .architecture-model.yaml.
        """
        return await check_gate(repo_path=repo_path, model_yaml=model_yaml)

    @mcp.tool()
    async def architect_pipeline(
        repo_path: str,
        stage: str = "",
        recursive: bool = True,
        resolutions: str = "",
        clear_cache: bool = False,
        scope: str = "",
    ) -> str:
        """Run the 10-stage extraction pipeline (stage-by-stage or all at once).

        Call this tool repeatedly, one stage at a time, to enable LLM enrichment
        between stages. Each call persists results to disk cache — subsequent
        calls resume from where the previous call left off.

        Stages (in dependency order):
            observe → infer → allocate → relate → specify → contract →
            validate → decompose → synthesize → emit

        Args:
            repo_path: Absolute path to the repository.
            stage: Run to specific stage (empty = all 10 stages).
                One of: observe, infer, allocate, relate, specify, contract,
                validate, decompose, synthesize, emit.
            recursive: Enable scoped sub-pipeline runs per system.
            resolutions: JSON string of resolved uncertainties from previous stage.
                Simplified format (only 3 fields required):
                [{"category": "...", "resolution": "...", "confidence": 0.9}]
                Optional fields: resolution_id, source, for_stage, model, total_tokens,
                files_sent, slices_sent, prompt_tokens, completion_tokens,
                target_name, target_kind, file_allocations ({target: [files]} or
                records), behavior_name, steps, source_files, and intent. Free-text
                resolution is evidence only and is never parsed into workflow steps.
            clear_cache: If true, discard cached stage results and re-run from scratch.
            scope: System ID/name/slug to run a scoped sub-pipeline on (after decompose).
                When set, only runs observe→validate for that system's files.

        Returns:
            JSON with: stages_completed, current_stage, from_cache, stages (scores),
            uncertainties_to_resolve, pipeline_report, lessons, artifacts_dir,
            llm_calls, total_llm_tokens.
        """
        import json

        parsed_resolutions = None
        if resolutions:
            try:
                parsed_resolutions = json.loads(resolutions)
            except json.JSONDecodeError:
                return json.dumps({"error": f"Invalid resolutions JSON: {resolutions[:100]}"})
        result = await run_pipeline(
            repo_path,
            stage=stage,
            recursive=recursive,
            resolutions=parsed_resolutions,
            clear_cache=clear_cache,
            scope=scope,
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    async def architect_assess(repo_path: str, conversation_text: str = "") -> dict:
        """CALL THIS after completing work, discovering issues, or when conversation reveals requirements. Extracts structured findings from recent context and stores locally."""
        from opencode_arch.mcp.tools.assess import assess_conversation

        return await assess_conversation(repo_path=repo_path, conversation_text=conversation_text)

    @mcp.tool()
    async def architect_evaluate(repo_path: str) -> dict:
        """CALL THIS for a health check of all 3 systems. Shows model coverage, requirement count, devlog activity, and sync status. Cached for 5 min."""
        from opencode_arch.mcp.tools.evaluate import evaluate_workspace

        return await evaluate_workspace(repo_path=repo_path)

    @mcp.tool()
    async def architect_sync(repo_path: str, dry_run: bool = False) -> dict:
        """CALL THIS at end of session or when evaluate shows unsynced findings. Pushes local findings to logs-db API with fuzzy dedup. Use dry_run=True to preview."""
        from opencode_arch.mcp.tools.sync import sync_findings

        return await sync_findings(repo_path=repo_path, dry_run=dry_run)

    @mcp.tool()
    async def architect_learn(
        learning_type: str,
        stage: str = "",
        condition: str = "",
        action: str = "",
        rationale: str = "",
        learned_from: str = "",
        name: str = "",
        indicators: str = "",
        problem: str = "",
        solution: str = "",
        trigger: str = "",
        diagnosis: str = "",
        fix_applied: str = "",
        validation: str = "",
        files_changed: str = "",
        commit: str = "",
        threshold_parameter: str = "",
        threshold_value: str = "",
    ) -> str:
        """Record a learning (heuristic, archetype, or workflow) to the global store."""
        return await record_learning(
            learning_type=learning_type,
            stage=stage,
            condition=condition,
            action=action,
            rationale=rationale,
            learned_from=learned_from,
            name=name,
            indicators=indicators,
            problem=problem,
            solution=solution,
            trigger=trigger,
            diagnosis=diagnosis,
            fix_applied=fix_applied,
            validation=validation,
            files_changed=files_changed,
            commit=commit,
            threshold_parameter=threshold_parameter,
            threshold_value=threshold_value,
        )

    from opencode_arch.mcp.tools.lifecycle.package_publish import publish_package_tool

    @mcp.tool()
    async def architect_package_publish(
        repo_path: str,
        model_yaml: str,
        manifest_json: str | None = None,
        parent_package_id: str | None = None,
    ) -> dict:
        """Publish an architecture package (model + optional manifest) to the repo's lifecycle store.

        Returns an envelope with {package_id, revision, digest, index_path}.
        Wraps architecture_model.lifecycle.publication.
        """
        return await publish_package_tool(
            repo_path=repo_path,
            model_yaml=model_yaml,
            manifest_json=manifest_json,
            parent_package_id=parent_package_id,
        )

    from opencode_arch.mcp.tools.lifecycle.package_load import package_load_tool
    from opencode_arch.mcp.tools.lifecycle.package_list_generations import (
        package_list_generations_tool,
    )

    @mcp.tool()
    async def architect_package_load(
        repo_path: str,
        revision: str | None = None,
    ) -> dict:
        """Load an architecture package generation (model + optional manifest).

        If ``revision`` is None, loads the CURRENT generation. Otherwise
        expects a 1-7 digit generation number (e.g. "0000001" or "1").
        Returns an envelope with {package_id, revision, model_yaml,
        manifest_json, root_digest, generation_dir}.
        """
        return await package_load_tool(
            repo_path=repo_path, revision=revision,
        )

    @mcp.tool()
    async def architect_package_list_generations(repo_path: str) -> dict:
        """List all committed generations of the root package.

        Returns an envelope with {package_id, current, generations}.
        ``current`` is the zero-padded revision pointed at by CURRENT,
        or None if no publication exists yet.
        """
        return await package_list_generations_tool(repo_path=repo_path)

    from opencode_arch.mcp.tools.lifecycle.package_diff import package_diff_tool

    @mcp.tool()
    async def architect_package_diff(
        repo_path: str,
        from_revision: str,
        to_revision: str,
    ) -> dict:
        """Semantic diff between two published generations of the root package.

        Both revisions must be 7-digit zero-padded generation ids
        (e.g. "0000001"). Returns an envelope with {from_revision,
        to_revision, diff}, where ``diff`` is the JSON-serialized
        ``SemanticDiff`` (entities, relationships, manifest, children, git).
        """
        return await package_diff_tool(
            repo_path=repo_path,
            from_revision=from_revision,
            to_revision=to_revision,
        )

    from opencode_arch.mcp.tools.lifecycle.package_children_add import (
        package_children_add_tool,
    )

    @mcp.tool()
    async def architect_package_children_add(
        repo_path: str,
        child_path: str,
    ) -> dict:
        """Append a child package.yaml to the root package's children list.

        ``child_path`` is a POSIX-relative path (relative to the root
        package directory ``<repo>/.architecture/lifecycle/``) pointing
        to an existing child ``package.yaml``. Returns an envelope with
        ``parent_architecture_id`` and the updated ``children`` list.
        """
        return await package_children_add_tool(
            repo_path=repo_path,
            child_path=child_path,
        )

    from opencode_arch.mcp.tools.lifecycle.package_stale import package_stale_tool

    @mcp.tool()
    async def architect_package_stale(
        repo_path: str,
        changed_paths: list[str],
    ) -> dict:
        """Report lifecycle nodes made stale by a set of changed paths.

        ``changed_paths`` is a list of POSIX-relative paths (relative to
        the root package directory). Returns an envelope with a
        ``stale`` list of records ``{node_id, kind, owned_paths, inputs,
        digest, reason}``, sorted by ``(kind, node_id)``. Does not write
        the ``.architecture/stale.yaml`` cache.
        """
        return await package_stale_tool(
            repo_path=repo_path,
            changed_paths=changed_paths,
        )

    from opencode_arch.mcp.tools.lifecycle.slice_materialize import (
        slice_materialize_tool,
    )

    @mcp.tool()
    async def architect_slice_materialize(
        repo_path: str,
        slice_spec: dict,
        persist: bool = True,
    ) -> dict:
        """Materialize a ModelSlice contract against the root package.

        ``slice_spec`` is the JSON-shaped ModelSlice payload (id,
        architecture_id, model_revision, scope, closure, shared_refs,
        selectors, and optional curation/parameters/generated_at).
        Returns an envelope with {slice_id, architecture_id,
        model_revision, digest, stub_entity_ids, warnings, fragment,
        persisted_path}. When ``persist=True``, writes the spec to
        ``<repo>/.architecture/lifecycle/slices/<slice_id>.yaml``.
        """
        return await slice_materialize_tool(
            repo_path=repo_path,
            slice_spec=slice_spec,
            persist=persist,
        )

    from opencode_arch.mcp.tools.lifecycle.view_project import view_project_tool

    @mcp.tool()
    async def architect_view_project(
        repo_path: str,
        view_spec: dict,
        slice_id: str,
    ) -> dict:
        """Project a ViewSpec over a persisted, materialized ModelSlice.

        ``view_spec`` is the JSON-shaped ViewSpec payload (id, slice_ref,
        projector, output_content_kind, ...). ``slice_id`` identifies a
        previously persisted slice at
        ``<repo>/.architecture/lifecycle/slices/<slice_id>.yaml``.
        Returns an envelope with {view_id, slice_id, model_revision,
        diagram_spec, provenance, warnings}.
        """
        return await view_project_tool(
            repo_path=repo_path,
            view_spec=view_spec,
            slice_id=slice_id,
        )

    from opencode_arch.mcp.tools.lifecycle.view_render import view_render_tool

    @mcp.tool()
    async def architect_view_render(
        repo_path: str,
        view_spec: dict,
        slice_id: str,
        artifact_spec: dict,
    ) -> dict:
        """Render a projected view via the named renderer.

        Projects ``view_spec`` over the persisted slice ``slice_id``, then
        invokes the renderer named by ``artifact_spec.renderer``
        (svg/markdown/html/ai-context). The ``zip`` renderer is rejected
        with PRECONDITION_FAILED — it requires a bundle resolver not
        exposed by this tool. Returns an envelope with {artifact_id,
        content_type, body_utf8, body_base64, digest, warnings}.
        """
        return await view_render_tool(
            repo_path=repo_path,
            view_spec=view_spec,
            slice_id=slice_id,
            artifact_spec=artifact_spec,
        )

    from opencode_arch.mcp.tools.lifecycle.artifact_plan import artifact_plan_tool

    @mcp.tool()
    async def architect_artifact_plan(
        repo_path: str,
        artifact_specs: list[dict],
    ) -> dict:
        """Build the topological rebuild plan for a set of ArtifactSpecs.

        ``artifact_specs`` is a non-empty list of JSON-shaped ArtifactSpec
        payloads (id, renderer, view_ref | bundle_refs, ...). Returns an
        envelope ``{"plan": {"nodes": [{"spec_id", "depends_on"}, ...],
        "order": [spec_id, ...]}}``. ``depends_on`` lists inbound edges
        (a zip's bundle_refs) sorted asc; ``nodes`` is sorted by
        spec_id; ``order`` is a deterministic Kahn topological sort.

        Errors: INVALID_ARGUMENT (empty/malformed input, duplicate ids),
        PRECONDITION_FAILED (DAG cycle, unknown bundle_ref).
        """
        return await artifact_plan_tool(
            repo_path=repo_path,
            artifact_specs=artifact_specs,
        )

    from opencode_arch.mcp.tools.lifecycle.artifact_rebuild import (
        architect_artifact_rebuild_tool,
    )

    @mcp.tool()
    async def architect_artifact_rebuild(
        repo_path: str,
        artifact_specs: list[dict],
        view_specs: list[dict],
        slice_specs: list[dict],
        force: bool = False,
    ) -> dict:
        """Rebuild artifacts from ArtifactSpec/ViewSpec/ModelSlice inputs.

        Executes the T11 rebuild pipeline: parses each artifact spec,
        resolves its view + slice from the parallel input lists,
        materializes the slice against the published architecture
        package, projects the view, renders bytes via the registered
        renderer, and atomically writes to
        ``.architecture/lifecycle/artifacts/<id>.<ext>``. Per-artifact
        failures are surfaced inside ``failed`` — the envelope still
        reports ``ok: True`` as long as the pipeline ran. Set
        ``force=True`` to rebuild even when ``expected_digest`` matches.

        Errors: INVALID_ARGUMENT (empty/non-list inputs, non-bool force),
        NOT_FOUND (missing repo_path).
        """
        return await architect_artifact_rebuild_tool(
            repo_path=repo_path,
            artifact_specs=artifact_specs,
            view_specs=view_specs,
            slice_specs=slice_specs,
            force=force,
        )

    from opencode_arch.mcp.tools.ai.workorder_submit import (
        architect_workorder_submit_tool,
    )

    @mcp.tool()
    async def architect_workorder_submit(
        repo_path: str,
        work_order: dict,
    ) -> dict:
        """Submit an AI WorkOrder and create its tracking Job.

        Parses ``work_order`` via
        :meth:`architecture_model.ai.work_order.WorkOrder.from_dict`,
        runs JSON-Schema validation, persists the WorkOrder atomically
        to ``.architecture/ai/workorders/<id>.yaml`` (idempotency guard:
        a second submission of the same id returns
        ``PRECONDITION_FAILED``), creates a ``draft``
        :class:`~architecture_model.ai.jobs.Job` via
        :class:`~architecture_model.ai.jobs.JobStore`, and appends an
        ``ai.workorder.submit`` event to
        ``.architecture/ai/workorders.journal.jsonl``. Success envelope:
        ``{"ok": True, "work_order_id", "job_id"}``.

        Errors: INVALID_ARGUMENT (non-dict ``work_order``), NOT_FOUND
        (missing ``repo_path``), SCHEMA_VIOLATION (parse or schema
        errors; ``details.errors: list[str]``), PRECONDITION_FAILED
        (duplicate id; ``details.work_order_id``, ``details.reason``).
        """
        return await architect_workorder_submit_tool(
            repo_path=repo_path,
            work_order=work_order,
        )

    from opencode_arch.mcp.tools.ai.job_get import architect_job_get_tool

    @mcp.tool()
    async def architect_job_get(repo_path: str, job_id: str) -> dict:
        """Fetch an AI Job by ``job_id``.

        Reads the per-job YAML persisted under
        ``.architecture/ai/jobs/<job_id>.yaml`` via
        :class:`~architecture_model.ai.jobs.JobStore` and returns the
        job as a dict. Success envelope: ``{"ok": True, "job": {...}}``.

        Errors: INVALID_ARGUMENT (empty/non-string ``job_id``),
        NOT_FOUND (``details.reason`` is ``"repo_missing"`` when
        ``repo_path`` does not exist, or ``"job_missing"`` when the job
        file is absent).
        """
        return await architect_job_get_tool(repo_path=repo_path, job_id=job_id)

    from opencode_arch.mcp.tools.ai.job_transition import (
        architect_job_transition_tool,
    )

    @mcp.tool()
    async def architect_job_transition(
        repo_path: str,
        job_id: str,
        new_state: str,
        reason: str | None = None,
        actor: str | None = None,
        result_ref: str | None = None,
        error: str | None = None,
    ) -> dict:
        """Transition an AI Job to ``new_state``.

        Delegates to
        :meth:`architecture_model.ai.jobs.JobStore.transition`, which
        appends a :class:`~architecture_model.ai.jobs.JobEvent` to the
        job history, updates the persisted YAML atomically, and journals
        an ``ai.job.transition`` event. ``actor`` defaults to
        ``"system"`` when ``None``. Transitioning to ``completed``
        requires ``result_ref``; transitioning to ``failed`` requires
        ``error``. Success envelope: ``{"ok": True, "job": {...}}``.

        Errors: INVALID_ARGUMENT (empty ``job_id``, unknown
        ``new_state`` — ``details.valid_states`` lists all
        :class:`~architecture_model.ai.jobs.JobState` values —, or
        missing accompanying field for a terminal transition),
        NOT_FOUND (``details.reason`` is ``"repo_missing"`` or
        ``"job_missing"``), PRECONDITION_FAILED (disallowed transition;
        ``details.from_state``, ``details.to_state``, ``details.allowed``
        as a sorted ``list[str]``).
        """
        return await architect_job_transition_tool(
            repo_path=repo_path,
            job_id=job_id,
            new_state=new_state,
            reason=reason,
            actor=actor,
            result_ref=result_ref,
            error=error,
        )

    from opencode_arch.mcp.tools.ai.job_run import architect_job_run_tool

    @mcp.tool()
    async def architect_job_run(repo_path: str, job_id: str) -> dict:
        """Execute a queued AI Job through the configured proposer plugin.

        Reads ``.architecture/ai/proposer_config.yaml`` (keys: ``plugin``
        as ``module.path:function_name``, optional ``enabled`` bool),
        resolves the callable via :mod:`importlib`, then delegates to
        :func:`opencode_arch.lifecycle_exec.worker.run_job`. Success
        envelope: ``{"ok": True, "job": {...}, "proposal_ref": <str|None>}``.
        When the worker marks the job ``failed`` (proposer error,
        non-Proposal return, or validation failure) the envelope still
        reports ``ok: True`` with ``proposal_ref: None`` and echoes the
        job's ``error`` at the envelope top level.

        Errors: INVALID_ARGUMENT (empty ``job_id``), NOT_FOUND
        (``details.reason`` in ``{"repo_missing", "job_missing",
        "workorder_missing"}``), PRECONDITION_FAILED
        (``details.reason`` in ``{"no_proposer_configured",
        "proposer_disabled", "proposer_config_malformed",
        "proposer_plugin_not_loadable", "proposer_plugin_not_callable",
        "job_not_queued"}``; ``job_not_queued`` includes
        ``details.state``), INTERNAL (unexpected worker failure).
        """
        return await architect_job_run_tool(
            repo_path=repo_path,
            job_id=job_id,
        )

    from opencode_arch.mcp.tools.ai.proposal_validate import (
        architect_proposal_validate_tool,
    )

    @mcp.tool()
    async def architect_proposal_validate(
        repo_path: str,
        proposal: dict,
        work_order_id: str,
        slice_ids: list[str],
    ) -> dict:
        """Validate an AI Proposal against its WorkOrder and input slices.

        Loads the persisted WorkOrder from
        ``.architecture/ai/workorders/<work_order_id>.yaml`` and each
        input slice from ``.architecture/lifecycle/slices/<slice_id>.yaml``,
        then dispatches to
        :func:`architecture_model.ai.validators.validate`. Success
        envelope: ``{"ok": True, "report": {"passed": bool,
        "findings": [{"severity", "message", "path", "code?"}, ...]}}``.
        An empty ``slice_ids`` list is allowed and simply skips the
        cross-revision drift check.

        Errors: INVALID_ARGUMENT (``proposal`` not a dict; empty /
        non-string ``work_order_id``; ``slice_ids`` not a list; any
        ``slice_id`` empty / non-string), NOT_FOUND
        (``details.reason`` in ``{"workorder_missing",
        "slice_missing"}``; also raised when ``repo_path`` does not
        exist), SCHEMA_VIOLATION (proposal parse error with
        ``details.errors``; or ``details.reason`` in
        ``{"workorder_malformed", "slice_malformed"}``), INTERNAL.
        """
        return await architect_proposal_validate_tool(
            repo_path=repo_path,
            proposal=proposal,
            work_order_id=work_order_id,
            slice_ids=slice_ids,
        )

    from opencode_arch.mcp.tools.ai.proposal_apply import (
        architect_proposal_apply_tool,
    )

    @mcp.tool()
    async def architect_proposal_apply(
        repo_path: str,
        proposal: dict,
        work_order_id: str,
        dry_run: bool = True,
    ) -> dict:
        """Apply a persisted, completed AI Proposal to the lifecycle store.

        Preconditions: the WorkOrder file must exist at
        ``.architecture/ai/workorders/<work_order_id>.yaml`` AND a Job
        referencing ``work_order_id`` must be in state ``completed`` AND
        that job's ``result_ref`` must point to a persisted proposal
        whose ``provenance.work_order_id`` and ``provenance.prompt_digest``
        match the caller's ``proposal`` (identity match).

        Success envelope: ``{"ok": True, "report": <ApplyReport as dict>}``.
        The ``report`` mirrors :class:`~opencode_arch.lifecycle_exec.apply.ApplyReport`
        with ``changes`` (list), ``new_revision`` (``str | None``),
        ``digest`` (``str | None``), and ``journal_events`` (list of dicts).

        On non-dry-run success, an ``ai.proposal.apply`` journal event is
        recorded IN ADDITION to the per-kind events already written by
        :func:`~opencode_arch.lifecycle_exec.apply.apply_proposal`. Dry
        runs and error paths never write this T19 event.

        Errors: INVALID_ARGUMENT (proposal not dict; empty work_order_id;
        non-bool dry_run), NOT_FOUND (repo missing;
        ``PackageNotFoundError`` from apply), SCHEMA_VIOLATION (proposal
        parse failed; ``InvalidProposalError`` from apply),
        PRECONDITION_FAILED (``details.reason`` in
        ``{"workorder_missing", "job_missing", "job_not_completed",
        "proposal_mismatch", "drift"}``; drift carries
        ``details.expected`` / ``details.actual``), INTERNAL (single-line
        message; no traceback leak).
        """
        return await architect_proposal_apply_tool(
            repo_path=repo_path,
            proposal=proposal,
            work_order_id=work_order_id,
            dry_run=dry_run,
        )

    from opencode_arch.mcp.tools.lifecycle.package_merge import (
        architect_package_merge_tool,
    )

    @mcp.tool()
    async def architect_package_merge(
        repo_path: str,
        base_revision: str,
        local_revision: str,
        remote_revision: str,
    ) -> dict:
        """Three-way merge of three published architecture package revisions.

        Loads the three named 7-digit revisions from the repo's root
        lifecycle package, runs
        :func:`opencode_arch.lifecycle_exec.merge.three_way_merge`, and:

        * If there are no conflicts, publishes the merged model as a new
          generation and records a ``lifecycle.package.merge`` journal
          event. Returns ``{ok: True, merged_digest, merged_revision,
          conflicts: [], stats}``.
        * If there are conflicts, does NOT publish and does NOT record a
          journal event. Returns ``{ok: True, merged_digest: None,
          conflicts: [...], stats}`` so the caller can resolve them.

        Errors: SCHEMA_VIOLATION (revision not ``^\\d{7}$``), NOT_FOUND
        (repo, package, or any of the three revisions missing —
        ``details.reason`` names which), PRECONDITION_FAILED (a revision's
        model file is malformed), INTERNAL (merge integrity failure or
        any other unexpected exception; no traceback leaked).
        """
        return await architect_package_merge_tool(
            repo_path=repo_path,
            base_revision=base_revision,
            local_revision=local_revision,
            remote_revision=remote_revision,
        )

    from opencode_arch.mcp.tools.component_health import component_health_tool

    @mcp.tool()
    async def architect_component_health(
        repo_path: str,
        component_id: str,
    ) -> dict:
        """Return the SI&L record + 7-day trend for a single component.

        Reads ``<repo_path>/.architecture/sil.sqlite`` (the shared SI&L
        event store populated by instrumented pipeline stages / MCP tools).

        Returns an envelope ``{ok: True, record: {...}, trend: {...}}`` where
        ``record`` mirrors the SILRecord serialization used by the snapshot
        writer (``component_id``, ``kind``, ``name``, ``metrics``,
        ``recent_events``) and ``trend`` is a distinct short summary
        ``{invocations_7d, failure_rate_7d, avg_duration_ms}``.

        Errors: INVALID_ARGUMENT (empty ``component_id``), NOT_FOUND
        (repo missing, SI&L store missing, or no events for the component).
        """
        return await component_health_tool(
            repo_path=repo_path,
            component_id=component_id,
        )

except ImportError:
    # mcp package not available - tools still work as standalone async functions
    mcp = None


if __name__ == "__main__":
    if mcp is not None:
        mcp.run()
    else:
        print("Error: mcp package not installed. Install with: pip install 'opencode-arch[mcp]'")
        raise SystemExit(1)
