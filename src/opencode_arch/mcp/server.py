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

    # --- B-ROUND round-centric surface (G1–G5) ---
    from opencode_arch.mcp.tools.arch_context import (
        arch_frontier as _arch_frontier,
        arch_gaps as _arch_gaps,
        arch_owed as _arch_owed,
        arch_slice as _arch_slice,
    )
    from opencode_arch.mcp.tools.arch_health import arch_health as _arch_health
    from opencode_arch.mcp.tools.arch_scan import arch_scan as _arch_scan
    from opencode_arch.mcp.tools.arch_extract import arch_extract as _arch_extract
    from opencode_arch.mcp.tools.arch_pipeline import arch_pipeline as _arch_pipeline
    from opencode_arch.mcp.tools.arch_validate import arch_validate as _arch_validate
    from opencode_arch.mcp.tools.arch_gate import arch_gate as _arch_gate
    from opencode_arch.mcp.tools.arch_check import arch_check as _arch_check
    from opencode_arch.mcp.tools.arch_evaluate import arch_evaluate as _arch_evaluate
    from opencode_arch.mcp.tools.arch_group import arch_group as _arch_group
    from opencode_arch.mcp.tools.arch_decompose import arch_decompose as _arch_decompose
    from opencode_arch.mcp.tools.arch_diff import arch_diff as _arch_diff
    from opencode_arch.mcp.tools.arch_docs import arch_docs as _arch_docs
    from opencode_arch.mcp.tools.arch_export import arch_export as _arch_export
    from opencode_arch.mcp.tools.arch_author import arch_author as _arch_author
    from opencode_arch.mcp.tools.arch_ingest import arch_ingest as _arch_ingest
    from opencode_arch.mcp.tools.arch_llm_audit import arch_llm_audit as _arch_llm_audit
    from opencode_arch.mcp.tools.arch_stats import arch_stats as _arch_stats
    from opencode_arch.mcp.tools.arch_require import arch_require as _arch_require
    from opencode_arch.mcp.tools.arch_trace_requirements import arch_trace_requirements as _arch_trace_requirements
    from opencode_arch.mcp.tools.arch_correct import arch_correct as _arch_correct
    from opencode_arch.mcp.tools.arch_feedback import arch_feedback as _arch_feedback
    from opencode_arch.mcp.tools.lifecycle.arch_package_publish import arch_package_publish as _arch_package_publish
    from opencode_arch.mcp.tools.lifecycle.arch_package_load import arch_package_load as _arch_package_load
    from opencode_arch.mcp.tools.lifecycle.arch_package_list_generations import arch_package_list_generations as _arch_package_list_generations
    from opencode_arch.mcp.tools.lifecycle.arch_package_diff import arch_package_diff as _arch_package_diff
    from opencode_arch.mcp.tools.lifecycle.arch_proposal_validate import arch_proposal_validate as _arch_proposal_validate
    from opencode_arch.mcp.tools.lifecycle.arch_proposal_apply import arch_proposal_apply as _arch_proposal_apply
    from opencode_arch.mcp.tools.lifecycle.arch_slice_materialize import arch_slice_materialize as _arch_slice_materialize
    from opencode_arch.mcp.tools.lifecycle.arch_view_project import arch_view_project as _arch_view_project
    from opencode_arch.mcp.tools.lifecycle.arch_view_render import arch_view_render as _arch_view_render
    from opencode_arch.mcp.tools.lifecycle.arch_package_children_add import arch_package_children_add as _arch_package_children_add
    from opencode_arch.mcp.tools.lifecycle.arch_package_stale import arch_package_stale as _arch_package_stale
    from opencode_arch.mcp.tools.lifecycle.arch_package_merge import arch_package_merge as _arch_package_merge
    from opencode_arch.mcp.tools.lifecycle.arch_artifact_plan import arch_artifact_plan as _arch_artifact_plan
    from opencode_arch.mcp.tools.lifecycle.arch_artifact_rebuild import arch_artifact_rebuild as _arch_artifact_rebuild
    from opencode_arch.mcp.tools.ai.arch_workorder_submit import arch_workorder_submit as _arch_workorder_submit
    from opencode_arch.mcp.tools.ai.arch_job_get import arch_job_get as _arch_job_get
    from opencode_arch.mcp.tools.ai.arch_job_transition import arch_job_transition as _arch_job_transition
    from opencode_arch.mcp.tools.ai.arch_job_run import arch_job_run as _arch_job_run
    from opencode_arch.mcp.tools.arch_work_issue import arch_work_issue as _arch_work_issue
    from opencode_arch.mcp.tools.arch_flags import arch_flags as _arch_flags
    from opencode_arch.mcp.tools.arch_observe import arch_observe as _arch_observe
    from opencode_arch.mcp.tools.arch_ingest_telemetry import (
        arch_ingest_telemetry as _arch_ingest_telemetry,
    )
    from opencode_arch.mcp.tools.arch_history import arch_history as _arch_history
    from opencode_arch.mcp.tools.arch_lessons import arch_lessons as _arch_lessons
    from opencode_arch.mcp.tools.arch_learn import arch_learn as _arch_learn
    from opencode_arch.mcp.tools.arch_learn_approve import arch_learn_approve as _arch_learn_approve
    from opencode_arch.mcp.tools.arch_round import arch_round as _arch_round
    from opencode_arch.mcp.tools.arch_grow import arch_grow as _arch_grow
    from opencode_arch.mcp.tools.arch_mine import arch_mine as _arch_mine
    from opencode_arch.mcp.tools.arch_compliance import arch_compliance as _arch_compliance
    from opencode_arch.mcp.tools.arch_cut import (
        arch_allocate_contract as _arch_allocate_contract,
        arch_propose_cut as _arch_propose_cut,
        arch_score_cut as _arch_score_cut,
    )
    from opencode_arch.mcp.tools.arch_integrate import (
        arch_integrate as _arch_integrate,
    )
    from opencode_arch.mcp.tools.arch_generation import (
        arch_bind as _arch_bind,
        arch_commit_generation as _arch_commit_generation,
    )

    @mcp.tool()
    async def arch_frontier(repo_path: str) -> dict:
        """Return the ready-promise frontier (node ids) for the round."""
        return await _arch_frontier(repo_path=repo_path)

    @mcp.tool()
    async def arch_owed(repo_path: str, node_id: str) -> dict:
        """Return valence-owed-but-absent attributes for an entity."""
        return await _arch_owed(repo_path=repo_path, node_id=node_id)

    @mcp.tool()
    async def arch_gaps(repo_path: str, node_id: str) -> dict:
        """Return G-DELIVERY typed gaps for an entity."""
        return await _arch_gaps(repo_path=repo_path, node_id=node_id)

    @mcp.tool()
    async def arch_slice(repo_path: str, node_id: str) -> dict:
        """Return the entity-scoped sub-doc for an entity."""
        return await _arch_slice(repo_path=repo_path, node_id=node_id)

    @mcp.tool()
    async def arch_health(repo_path: str, node_id: str | None = None) -> dict:
        """Return per-node (with flags) or graph-wide health projection."""
        return await _arch_health(repo_path=repo_path, node_id=node_id)

    @mcp.tool()
    async def arch_scan(repo_path: str, mode: str = "full") -> dict:
        """Return the module / import-edge inventory of the repo's source tree."""
        return await _arch_scan(repo_path=repo_path, mode=mode)

    @mcp.tool()
    async def arch_extract(
        repo_path: str, model_yaml: str = "", context_tokens: int = 0
    ) -> dict:
        """Extract a v3 model from source and commit a generation."""
        return await _arch_extract(
            repo_path=repo_path,
            model_yaml=model_yaml,
            context_tokens=context_tokens,
        )

    @mcp.tool()
    async def arch_pipeline(
        repo_path: str,
        stage: str = "",
        recursive: bool = True,
        resolutions: list[dict] | None = None,
        clear_cache: bool = False,
        scope: str = "",
    ) -> dict:
        """Run the openAG B-ROUND pipeline over source and commit a generation."""
        return await _arch_pipeline(
            repo_path=repo_path,
            stage=stage,
            recursive=recursive,
            resolutions=resolutions,
            clear_cache=clear_cache,
            scope=scope,
        )

    @mcp.tool()
    async def arch_validate(repo_path: str = "", model_yaml: str = "") -> dict:
        """Validate a model (schema + axis lint) and return a bounded score."""
        return await _arch_validate(repo_path=repo_path, model_yaml=model_yaml)

    @mcp.tool()
    async def arch_gate(repo_path: str = "", model_yaml: str = "") -> dict:
        """Run the L2 development gate (owed+completeness gaps, scored)."""
        return await _arch_gate(repo_path=repo_path, model_yaml=model_yaml)

    @mcp.tool()
    async def arch_check(repo_path: str = "", model_yaml: str = "") -> dict:
        """Check model representativeness against the code ground graph."""
        return await _arch_check(repo_path=repo_path, model_yaml=model_yaml)

    @mcp.tool()
    async def arch_evaluate(repo_path: str = "") -> dict:
        """Health check: coverage, health score, promise rollup, requirement count."""
        return await _arch_evaluate(repo_path=repo_path)

    @mcp.tool()
    async def arch_group(repo_path: str = "", target_groups: int = 0, model_yaml: str = "") -> dict:
        """Group repository modules by the model's A1 containment partition."""
        return await _arch_group(repo_path=repo_path, target_groups=target_groups, model_yaml=model_yaml)

    @mcp.tool()
    async def arch_decompose(repo_path: str = "", model_yaml: str = "") -> dict:
        """Report the model's System-level decomposition and split candidates."""
        return await _arch_decompose(repo_path=repo_path, model_yaml=model_yaml)

    @mcp.tool()
    async def arch_diff(repo_path: str = "", model_a_yaml: str = "", model_b_yaml: str = "") -> dict:
        """Diff two architecture model docs (model_b defaults to git HEAD)."""
        return await _arch_diff(repo_path=repo_path, model_a_yaml=model_a_yaml, model_b_yaml=model_b_yaml)

    @mcp.tool()
    async def arch_docs(repo_path: str = "", formats: str = "all", model_yaml: str = "") -> dict:
        """Generate openAG-shaped SE documentation from the model."""
        return await _arch_docs(repo_path=repo_path, formats=formats, model_yaml=model_yaml)

    @mcp.tool()
    async def arch_export(repo_path: str = "", output_dir: str = "", fmt: str = "graphml", model_yaml: str = "") -> dict:
        """Export the model as a graph file (graphml/json-graph) to a directory."""
        return await _arch_export(repo_path=repo_path, output_dir=output_dir, fmt=fmt, model_yaml=model_yaml)

    @mcp.tool()
    async def arch_author(repo_path: str = "", requirements_text: str = "") -> dict:
        """Forward-author a concept-phase model from requirements and record a generation."""
        return await _arch_author(repo_path=repo_path, requirements_text=requirements_text)

    @mcp.tool()
    async def arch_ingest(repo_path: str = "", source_graph_json: str = "") -> dict:
        """Ingest a SourceGraph JSON string into a deterministic openAG model doc."""
        return await _arch_ingest(repo_path=repo_path, source_graph_json=source_graph_json)

    @mcp.tool()
    async def arch_llm_audit(repo_path: str = "", model_yaml: str = "") -> dict:
        """Run a deterministic decomposition second-opinion audit over the model."""
        return await _arch_llm_audit(repo_path=repo_path, model_yaml=model_yaml)

    @mcp.tool()
    async def arch_stats(repo_path: str = "", tool_filter: str = "") -> dict:
        """Aggregate per-tool telemetry and optional model rollup for the repo."""
        return await _arch_stats(repo_path=repo_path, tool_filter=tool_filter)

    @mcp.tool()
    async def arch_require(repo_path: str = "", requirement: str = "", component_id: str = "", priority: str = "must", context: str = "") -> dict:
        """Capture a MoSCoW-prioritized functional requirement for the repo."""
        return await _arch_require(repo_path=repo_path, requirement=requirement, component_id=component_id, priority=priority, context=context)

    @mcp.tool()
    async def arch_trace_requirements(repo_path: str = "", model_yaml: str = "", requirements_yaml: str = "") -> dict:
        """Trace requirements (from arg or the repo ledger) to model entities."""
        return await _arch_trace_requirements(repo_path=repo_path, model_yaml=model_yaml, requirements_yaml=requirements_yaml)

    @mcp.tool()
    async def arch_correct(repo_path: str = "", correction_type: str = "", target: str = "", reason: str = "", suggestion: dict | None = None) -> dict:
        """Store a structured architecture-model correction for the repo."""
        return await _arch_correct(repo_path=repo_path, correction_type=correction_type, target=target, reason=reason, suggestion=suggestion)

    @mcp.tool()
    async def arch_feedback(repo_path: str = "", feedback_type: str = "", content: str = "", context: dict | None = None, rating: int | None = None, correction: dict | None = None) -> dict:
        """Record user feedback for model improvement into the repo ledger."""
        return await _arch_feedback(repo_path=repo_path, feedback_type=feedback_type, content=content, context=context, rating=rating, correction=correction)

    @mcp.tool()
    async def arch_package_publish(repo_path: str = "", model_yaml: str = "", reason: str = "") -> dict:
        """Publish the repo's model as the next openAG generation snapshot."""
        return await _arch_package_publish(repo_path=repo_path, model_yaml=model_yaml, reason=reason)

    @mcp.tool()
    async def arch_package_load(repo_path: str = "", gen_id: str = "") -> dict:
        """Load a published openAG generation snapshot (latest when gen_id empty)."""
        return await _arch_package_load(repo_path=repo_path, gen_id=gen_id)

    @mcp.tool()
    async def arch_package_list_generations(repo_path: str = "") -> dict:
        """List published openAG generation snapshots in store order."""
        return await _arch_package_list_generations(repo_path=repo_path)

    @mcp.tool()
    async def arch_package_diff(repo_path: str = "", gen_a: str = "", gen_b: str = "") -> dict:
        """Diff two published openAG generation snapshots."""
        return await _arch_package_diff(repo_path=repo_path, gen_a=gen_a, gen_b=gen_b)

    @mcp.tool()
    async def arch_proposal_validate(repo_path: str = "", proposal: dict | None = None, model_yaml: str = "", task_class: str = "", prompt_digest: str = "") -> dict:
        """Validate a typed proposal against an openAG model doc."""
        return await _arch_proposal_validate(repo_path=repo_path, proposal=proposal, model_yaml=model_yaml, task_class=task_class, prompt_digest=prompt_digest)

    @mcp.tool()
    async def arch_proposal_apply(repo_path: str = "", proposal: dict | None = None, model_yaml: str = "", task_class: str = "", prompt_digest: str = "", reason: str = "", dry_run: bool = False) -> dict:
        """Apply a typed proposal to an openAG model doc and publish a generation."""
        return await _arch_proposal_apply(repo_path=repo_path, proposal=proposal, model_yaml=model_yaml, task_class=task_class, prompt_digest=prompt_digest, reason=reason, dry_run=dry_run)

    @mcp.tool()
    async def arch_slice_materialize(repo_path: str = "", entity_id: str = "", model_yaml: str = "") -> dict:
        """Materialize an entity-scoped slice of an openAG model doc."""
        return await _arch_slice_materialize(repo_path=repo_path, entity_id=entity_id, model_yaml=model_yaml)

    @mcp.tool()
    async def arch_view_project(repo_path: str = "", entity_id: str = "", model_yaml: str = "") -> dict:
        """Project an openAG model doc into a viewer payload view."""
        return await _arch_view_project(repo_path=repo_path, entity_id=entity_id, model_yaml=model_yaml)

    @mcp.tool()
    async def arch_view_render(repo_path: str = "", model_yaml: str = "") -> dict:
        """Render an openAG model doc into the self-contained viewer HTML."""
        return await _arch_view_render(repo_path=repo_path, model_yaml=model_yaml)

    @mcp.tool()
    async def arch_package_children_add(repo_path: str = "", child_ref: str = "", revision: str = "") -> dict:
        """Append a child package ref to the repo's deterministic child-refs ledger."""
        return await _arch_package_children_add(repo_path=repo_path, child_ref=child_ref, revision=revision)

    @mcp.tool()
    async def arch_package_stale(repo_path: str = "", changed_paths: list[str] | None = None, model_yaml: str = "") -> dict:
        """Return entities made stale by changed_paths, anchored to the latest generation."""
        return await _arch_package_stale(repo_path=repo_path, changed_paths=changed_paths, model_yaml=model_yaml)

    @mcp.tool()
    async def arch_package_merge(repo_path: str = "", base_revision: str = "", local_revision: str = "", remote_revision: str = "") -> dict:
        """Three-way merge base/local/remote generation snapshots into a new generation."""
        return await _arch_package_merge(repo_path=repo_path, base_revision=base_revision, local_revision=local_revision, remote_revision=remote_revision)

    @mcp.tool()
    async def arch_artifact_plan(repo_path: str = "", artifact_specs: list[dict] | None = None) -> dict:
        """Return the deterministic topological rebuild plan for artifact_specs."""
        return await _arch_artifact_plan(repo_path=repo_path, artifact_specs=artifact_specs)

    @mcp.tool()
    async def arch_artifact_rebuild(repo_path: str = "", artifact_specs: list[dict] | None = None, force: bool = False) -> dict:
        """Render + write openAG artifacts over the live model doc via the viewer."""
        return await _arch_artifact_rebuild(repo_path=repo_path, artifact_specs=artifact_specs, force=force)

    @mcp.tool()
    async def arch_workorder_submit(repo_path: str = "", work_order: dict | None = None) -> dict:
        """Persist an AI WorkOrder, create its draft tracking Job, and journal the submission."""
        return await _arch_workorder_submit(repo_path=repo_path, work_order=work_order)

    @mcp.tool()
    async def arch_job_get(repo_path: str = "", job_id: str = "") -> dict:
        """Fetch a persisted AI Job by id."""
        return await _arch_job_get(repo_path=repo_path, job_id=job_id)

    @mcp.tool()
    async def arch_job_transition(
        repo_path: str = "",
        job_id: str = "",
        new_state: str = "",
        reason: str | None = None,
        actor: str | None = None,
        result_ref: str | None = None,
        error: str | None = None,
    ) -> dict:
        """Transition an AI Job to a new state (guards terminal transitions)."""
        return await _arch_job_transition(
            repo_path=repo_path,
            job_id=job_id,
            new_state=new_state,
            reason=reason,
            actor=actor,
            result_ref=result_ref,
            error=error,
        )

    @mcp.tool()
    async def arch_job_run(repo_path: str = "", job_id: str = "") -> dict:
        """Execute a queued AI Job via the configured proposer plugin."""
        return await _arch_job_run(repo_path=repo_path, job_id=job_id)

    @mcp.tool()
    async def arch_work_issue(
        repo_path: str = "",
        issue_id: int = 0,
        dry_run: bool = False,
        force: bool = False,
    ) -> dict:
        """Execute the comment→issue→dev ceremony loop for one logs-db issue."""
        return await _arch_work_issue(
            repo_path=repo_path,
            issue_id=issue_id,
            dry_run=dry_run,
            force=force,
        )

    @mcp.tool()
    async def arch_flags(repo_path: str, node_id: str | None = None) -> dict:
        """Return proprioceptive anomaly flags (workspace-wide or node-filtered)."""
        return await _arch_flags(repo_path=repo_path, node_id=node_id)

    @mcp.tool()
    async def arch_observe(
        repo_path: str,
        component_id: str | None = None,
        io_kind: str | None = None,
        since: str | None = None,
    ) -> dict:
        """Return raw filtered runtime observation records (live proprioception)."""
        return await _arch_observe(
            repo_path=repo_path,
            component_id=component_id,
            io_kind=io_kind,
            since=since,
        )

    @mcp.tool()
    async def arch_ingest_telemetry(repo_path: str, events: list[dict]) -> dict:
        """Append externally-supplied observation events to the journal."""
        return await _arch_ingest_telemetry(repo_path=repo_path, events=events)

    @mcp.tool()
    async def arch_history(
        repo_path: str,
        node_id: str | None = None,
        gen_a: str | None = None,
        gen_b: str | None = None,
    ) -> dict:
        """Return the generation timeline, a node trajectory, or a generation diff."""
        return await _arch_history(
            repo_path=repo_path,
            node_id=node_id,
            gen_a=gen_a,
            gen_b=gen_b,
        )

    @mcp.tool()
    async def arch_lessons(repo_path: str) -> dict:
        """Return mined lessons + reviewable proposal stubs (proprioception)."""
        return await _arch_lessons(repo_path=repo_path)

    @mcp.tool()
    async def arch_learn(
        repo_path: str,
        subject: str | None = None,
        lesson_type: str | None = None,
    ) -> dict:
        """Materialize a draft WorkOrder from the top mined lesson (gated)."""
        return await _arch_learn(
            repo_path=repo_path, subject=subject, lesson_type=lesson_type
        )

    @mcp.tool()
    async def arch_learn_approve(
        repo_path: str = "",
        job_id: str = "",
        dry_run: bool = False,
    ) -> dict:
        """Release a draft learning Job: author via proposer, then apply+publish."""
        return await _arch_learn_approve(
            repo_path=repo_path, job_id=job_id, dry_run=dry_run
        )

    @mcp.tool()
    async def arch_round(repo_path: str, node_id: str | None = None) -> dict:
        """Run the B-ROUND least-fixpoint (whole-graph or node-scoped)."""
        return await _arch_round(repo_path=repo_path, node_id=node_id)

    @mcp.tool()
    async def arch_grow(repo_path: str, root: str, budget: float = 100.0,
                        max_iterations: int = 8, model: str | None = None,
                        no_provider: bool = False) -> dict:
        """Standalone scoped forward-GROW operator."""
        return await _arch_grow(repo_path=repo_path, root=root, budget=budget,
                                max_iterations=max_iterations, model=model,
                                no_provider=no_provider)

    @mcp.tool()
    async def arch_mine(repo_path: str = "", db: str = "", reservoir: str = "",
                        ledger: str = "", repo: str | None = None,
                        session: str | None = None,
                        model: str | None = None) -> dict:
        """Run the openAG reservoir-mining pass over opencode sessions."""
        return await _arch_mine(repo_path=repo_path, db=db, reservoir=reservoir,
                                ledger=ledger, repo=repo, session=session,
                                model=model)

    @mcp.tool()
    async def arch_compliance(repo_path: str = "", report: str = "matrix") -> dict:
        """Return an openAG compliance report (matrix | axes | scoring)."""
        return await _arch_compliance(repo_path=repo_path, report=report)

    @mcp.tool()
    async def arch_propose_cut(repo_path: str, node_id: str, proposal: dict) -> dict:
        """Apply a partition-refinement proposal via the gated-write path."""
        return await _arch_propose_cut(
            repo_path=repo_path, node_id=node_id, proposal=proposal
        )

    @mcp.tool()
    async def arch_score_cut(
        nodes: list[str], edges: list[list[str]], cells: list[list[str]]
    ) -> dict:
        """Score a candidate cut of a ground-graph slice (pure read)."""
        return await _arch_score_cut(nodes=nodes, edges=edges, cells=cells)

    @mcp.tool()
    async def arch_allocate_contract(interface_cut: dict) -> dict:
        """Allocate producer/consumer child contracts (A2 down-law, pure)."""
        return await _arch_allocate_contract(interface_cut=interface_cut)

    @mcp.tool()
    async def arch_integrate(
        children: list[dict],
        interface_id: str,
        parent_guarantee: dict | None = None,
    ) -> dict:
        """Run the B3 integration round over an interface's children (pure)."""
        return await _arch_integrate(
            children=children,
            interface_id=interface_id,
            parent_guarantee=parent_guarantee,
        )

    @mcp.tool()
    async def arch_bind(repo_path: str) -> dict:
        """θ-crosswalk the latest generation onto the current model (pure read)."""
        return await _arch_bind(repo_path=repo_path)

    @mcp.tool()
    async def arch_commit_generation(repo_path: str) -> dict:
        """Record the current model as the next monotone generation."""
        return await _arch_commit_generation(repo_path=repo_path)

except ImportError:
    # mcp package not available - tools still work as standalone async functions
    mcp = None


if __name__ == "__main__":
    if mcp is not None:
        mcp.run()
    else:
        print("Error: mcp package not installed. Install with: pip install 'opencode-arch[mcp]'")
        raise SystemExit(1)
