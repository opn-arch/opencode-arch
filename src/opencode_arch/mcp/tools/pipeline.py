"""architect_pipeline MCP tool — run the 10-stage extraction pipeline.

Supports stage-by-stage execution with file-based cache persistence.
The MCP orchestrator calls this tool once per stage, reviews uncertainties,
resolves them via LLM, and passes resolutions on the next call.

For subsystem enrichment, use the `scope` parameter after decompose to run
scoped pipelines on individual detected systems.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from opencode_arch.mcp.quality import with_quality


def _slugify(name: str) -> str:
    """Convert name to filesystem-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _write_sil_snapshots(repo_root: Path) -> None:
    """Materialize per-component SIL snapshots to ``<repo>/.architecture/sil/<comp>.yaml``.

    Called at the tail of a successful pipeline run as the plan's "cron
    hook" — a periodic YAML materialization of the SQLite store. All
    exceptions are swallowed by the caller so pipeline runs are never
    blocked by snapshot failures.
    """
    sil_db = repo_root / ".architecture" / "sil.sqlite"
    if not sil_db.exists():
        return
    from opencode_arch.sil.store import SILStore
    from opencode_arch.sil.snapshot import write_snapshot

    store = SILStore(sil_db)
    out_dir = repo_root / ".architecture" / "sil"
    for comp_id in store.distinct_component_ids():
        try:
            write_snapshot(store, comp_id, out_dir / f"{_slugify(comp_id)}.yaml")
        except Exception:
            # per-component failures are non-fatal.
            continue


@with_quality
async def run_pipeline(
    repo_path: str,
    stage: str = "",
    recursive: bool = True,
    resolutions: list[dict[str, Any]] | None = None,
    clear_cache: bool = False,
    scope: str = "",
) -> dict[str, Any]:
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
        recursive: If True, synthesize stage runs scoped sub-pipelines
            for each detected system.
        resolutions: List of resolved uncertainties from the previous stage.
            Each dict: {category, resolution, confidence, source}. Optional
            deterministic metadata: resolution_id, for_stage, files_sent,
            file_allocations ({target_name: [files]} or records with target_name,
            files, and target_kind), behavior_name, steps, source_files, and intent.
            These are converted to Evidence and applied before running.
        clear_cache: If True, clear cached results before running.
        scope: System ID to run a scoped sub-pipeline on (e.g., "SYS-1").
            Requires decompose to have been run first (top-level cache).
            Uses per-system cache at .architecture/pipeline-cache/<system-slug>/.

    Returns:
        dict with stages_completed, current_stage, from_cache, stages (scores),
        uncertainties_to_resolve, pipeline_report, lessons, artifacts_dir,
        llm_calls, total_llm_tokens.
        When scope is used, also returns: scope, system_name, system_files.
    """
    root = Path(repo_path).resolve()
    if not root.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}
    resolution_ids = [
        str(item.get("resolution_id"))
        for item in resolutions or []
        if item.get("resolution_id")
    ]
    duplicate_ids = sorted({item for item in resolution_ids if resolution_ids.count(item) > 1})
    if duplicate_ids:
        return {"error": f"Duplicate resolution_id values: {', '.join(duplicate_ids)}"}

    output_dir = root
    learning_path = root / ".architecture" / "learning"

    try:
        from architecture_model.pipeline import (
            PipelineCache,
            PipelineCoordinator,
            PipelineContext,
            LearningStore,
            LLMCallRecord,
            LessonEntry,
            generate_lessons,
            generate_pipeline_report,
        )
        from architecture_model.pipeline.protocol import Evidence
        from architecture_model.pipeline.observe import ObserveStage
        from architecture_model.pipeline.infer import InferStage
        from architecture_model.pipeline.allocate import AllocateStage
        from architecture_model.pipeline.relate import RelateStage
        from architecture_model.pipeline.specify import SpecifyStage
        from architecture_model.pipeline.contract import ContractStage
        from architecture_model.pipeline.validate import ValidateStage
        from architecture_model.pipeline.decompose import DecomposeStage
        from architecture_model.pipeline.synthesize import SynthesizeStage
        from architecture_model.pipeline.emit import EmitStage

        # Determine cache directory (scoped or top-level)
        top_cache_dir = root / ".architecture" / "pipeline-cache"

        if scope:
            # Scoped run: load decompose result from top-level cache to get system boundary
            top_cache = PipelineCache(top_cache_dir)
            decompose_result_sr = top_cache.load_stage("decompose")
            if decompose_result_sr is None:
                return {
                    "error": "Scoped run requires decompose to have been run first. Run architect_pipeline(stage='decompose') first."
                }

            decompose_result = decompose_result_sr.output
            # Find the matching system boundary
            boundary = None
            for sys in decompose_result.systems:
                if (
                    sys.system_id == scope
                    or sys.name == scope
                    or _slugify(sys.name) == _slugify(scope)
                ):
                    boundary = sys
                    break
            if boundary is None:
                available = [f"{s.system_id} ({s.name})" for s in decompose_result.systems]
                return {"error": f"System '{scope}' not found. Available: {available}"}

            cache_dir = top_cache_dir / _slugify(boundary.name)
            scope_files = [Path(f) for f in boundary.files]
            system_name = boundary.name
        else:
            cache_dir = top_cache_dir
            scope_files = []
            system_name = root.name

        # Initialize cache
        cache = PipelineCache(cache_dir)
        if clear_cache:
            cache.clear()

        # For scoped runs, only use stages up to validate (no decompose/synthesize/emit)
        if scope:
            stages = {
                "observe": ObserveStage(),
                "infer": InferStage(),
                "allocate": AllocateStage(),
                "relate": RelateStage(),
                "specify": SpecifyStage(),
                "contract": ContractStage(),
                "validate": ValidateStage(),
            }
        else:
            stages = {
                "observe": ObserveStage(),
                "infer": InferStage(),
                "allocate": AllocateStage(),
                "relate": RelateStage(),
                "specify": SpecifyStage(),
                "contract": ContractStage(),
                "validate": ValidateStage(),
                "decompose": DecomposeStage(),
                "synthesize": SynthesizeStage(),
                "emit": EmitStage(),
            }

        store = LearningStore(learning_path)
        coord = PipelineCoordinator(stages, learning_store=store)
        ctx = PipelineContext(repo_path=root, output_dir=output_dir)
        ctx.config["coordinator"] = coord

        # Wire up LLM enrichment via copilot-relay if available
        try:
            from opencode_arch.llm.relay import relay_llm_callback, is_relay_available

            if is_relay_available():
                ctx.llm_callback = relay_llm_callback
        except Exception:
            pass  # No relay available — deterministic mode

        # Set scope if scoped run
        if scope:
            ctx.scope = boundary.system_id
            ctx.scope_files = scope_files

        # Hydrate context from cache (resume from previous calls)
        cached_stages = cache.hydrate_context(ctx)

        # Apply resolutions as evidence + LLM call records
        if resolutions:
            stage_order = list(stages)
            rerun_from = min(
                (
                    stage_order.index(res.get("for_stage", stage or "unknown"))
                    for res in resolutions
                    if res.get("for_stage", stage or "unknown") in stage_order
                ),
                default=len(stage_order),
            )
            for affected_stage in stage_order[rerun_from:]:
                ctx.cache.pop(affected_stage, None)
                if affected_stage in cached_stages:
                    cached_stages.remove(affected_stage)
            cache.invalidate(stage_order[rerun_from:])
            for res in resolutions:
                ev = Evidence(
                    source=res.get("source", "llm_analysis"),
                    confidence=res.get("confidence", 0.8),
                    raw=res.get("resolution", ""),
                    location=res.get("category", ""),
                    metadata={
                        key: res[key]
                        for key in (
                            "resolution_id", "for_stage", "files_sent", "target_name",
                            "target_kind", "file_allocations", "behavior_name",
                            "steps", "source_files", "intent",
                        )
                        if key in res
                    },
                )
                ctx.prior_corrections.append(ev)

                # Record LLM call for each resolution
                ctx.llm_calls.append(
                    LLMCallRecord(
                        stage=res.get("for_stage", stage or "unknown"),
                        purpose=f"resolve uncertainty: {res.get('category', 'unknown')}",
                        resolution_id=res.get("resolution_id", ""),
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
                        model=res.get("model", ""),
                        prompt_tokens=res.get("prompt_tokens", 0),
                        completion_tokens=res.get("completion_tokens", 0),
                        total_tokens=res.get("total_tokens", 0),
                        duration_ms=res.get("duration_ms", 0),
                        confidence=res.get("confidence", 0.8),
                        items_produced=1,
                        notes=res.get("resolution", ""),
                        files_sent=res.get("files_sent", []),
                        slices_sent=res.get("slices_sent", []),
                    )
                )

        # Run pipeline
        if stage:
            results = coord.run_to(stage, ctx)
        else:
            results = coord.run_all(ctx)

        # LLM enrichment: enrich all enrichable stages, then re-run downstream
        enrichment_changes: list[str] = []
        if ctx.llm_callback is not None:
            enrichable = ["infer", "allocate"]
            any_enriched = False
            for enrich_stage in enrichable:
                if enrich_stage in results:
                    try:
                        changes = await coord.enrich_stage_output(enrich_stage, ctx)
                        enrichment_changes.extend(changes)
                        if changes:
                            any_enriched = True
                            # Save enriched result to cache
                            cache.save_stage(enrich_stage, results[enrich_stage])
                    except Exception:
                        pass

            # If enrichment changed anything and we ran past synthesize,
            # re-run synthesize+emit with the enriched data
            if any_enriched and not stage:
                # Invalidate downstream stages so they re-run
                for downstream in ["synthesize", "emit"]:
                    ctx.cache.pop(downstream, None)
                    results.pop(downstream, None)
                try:
                    re_results = coord.run_to("emit", ctx)
                    results.update(re_results)
                    for name, r in re_results.items():
                        cache.save_stage(name, r)
                except Exception:
                    pass

        # Persist newly computed stages to cache
        for name, result in results.items():
            if name not in cached_stages:
                cache.save_stage(name, result)
        cache.save_llm_calls(ctx.llm_calls)

        # Persist enrichment log and artifact reviews
        if ctx.enrichment_log:
            cache.save_enrichment_log(ctx.enrichment_log)
        if hasattr(ctx, "_artifact_reviews") and ctx._artifact_reviews:
            cache.save_reviews(ctx._artifact_reviews)

        # Build stage summaries
        stage_summaries = {}
        for name, result in results.items():
            stage_summaries[name] = {
                "score": result.quality.score,
                "duration_ms": result.duration_ms,
                "diagnostics": len(result.diagnostics),
                "uncertainties": len(result.uncertainties),
                "from_cache": name in cached_stages,
            }

        # Collect uncertainties from the target stage for the agent to resolve
        target_stage_name = stage or list(results.keys())[-1]
        target_result = results.get(target_stage_name)
        uncertainties_to_resolve = []
        if target_result and target_result.uncertainties:
            for u in target_result.uncertainties:
                uncertainties_to_resolve.append(
                    {
                        "category": u.category,
                        "description": u.description,
                        "context": u.context,
                        "suggested_fallback": u.suggested_fallback,
                        "priority": u.priority,
                    }
                )

        # Generate report and lessons
        report = generate_pipeline_report(results, system_name=system_name, llm_calls=ctx.llm_calls)

        lesson_entries: list[LessonEntry] = []
        for name, result in results.items():
            lesson_entries.extend(LessonEntry.from_diagnostics(name, result.diagnostics))
            lesson_entries.extend(LessonEntry.from_uncertainties(name, result.uncertainties))
            stage_llm = [c for c in ctx.llm_calls if c.stage == name]
            lesson_entries.extend(LessonEntry.from_llm_calls(name, stage_llm))
        lessons = generate_lessons(lesson_entries, system_name=system_name)

        # LLM call summaries
        llm_summaries = []
        for call in ctx.llm_calls:
            llm_summaries.append(
                {
                    "stage": call.stage,
                    "purpose": call.purpose,
                    "tokens": call.total_tokens,
                    "model": call.model,
                    "cached": call.cached,
                    "files_sent": call.files_sent,
                }
            )

        # Record telemetry
        try:
            from opencode_arch.telemetry.collector import drain_and_store

            drain_and_store(tool="architect_pipeline", repo=root.name)
        except Exception:
            pass

        # Auto-log progress for each completed stage
        try:
            from .log import log_entry

            for name, result in results.items():
                if name not in cached_stages:
                    await log_entry(
                        repo_path=repo_path,
                        log_type="progress",
                        title=f"Pipeline stage '{name}' completed (score: {result.quality.score})",
                        context={"stage": name, "score": result.quality.score, "from_cache": False},
                    )
        except Exception:
            pass  # best-effort logging

        # Auto-regenerate live artifacts
        try:
            from pathlib import Path as _PathRegen
            import sys

            sys.path.insert(0, str(_PathRegen(repo_path).resolve()))
            from architecture_model.core.parser import load_model as _load_regen
            from architecture_model.docs.generator import generate_docs as _generate_live_docs

            _model_file_regen = _PathRegen(repo_path) / ".architecture-model.yaml"
            if _model_file_regen.exists():
                _regen_model = _load_regen(str(_model_file_regen))
                _regen_output_dir = _PathRegen(repo_path) / ".architecture" / "docs"
                _regen_output_dir.mkdir(parents=True, exist_ok=True)
                _generate_live_docs(_regen_model, _regen_output_dir)
        except Exception:
            pass  # Non-fatal — live artifact regen is best-effort

        response = {
            "stages_completed": list(results.keys()),
            "current_stage": target_stage_name,
            "from_cache": cached_stages,
            "stages": stage_summaries,
            "uncertainties_to_resolve": uncertainties_to_resolve,
            "pipeline_report": report,
            "lessons": lessons,
            "artifacts_dir": str(output_dir),
            "llm_calls": llm_summaries,
            "total_llm_tokens": sum(c.total_tokens for c in ctx.llm_calls),
            "enrichment_changes": enrichment_changes,
            "artifact_reviews": len(getattr(ctx, "_artifact_reviews", []) or []),
            "enrichment_records": len(ctx.enrichment_log),
            "hint": "Use architect_log to record decisions made during this stage.",
        }

        # Compute and include completeness grade
        try:
            from architecture_model.core.completeness import compute_completeness
            from architecture_model.core.parser import load_model as _load_comp

            model_file = root / ".architecture-model.yaml"
            if model_file.exists():
                comp_model = _load_comp(model_file)
                comp_result = compute_completeness(comp_model)
                response["completeness"] = {
                    "score": comp_result.score,
                    "grade": comp_result.grade,
                    "dimensions": comp_result.dimensions,
                    "gaps": comp_result.gaps,
                }
            # Also check SoS model
            sos_file = root / ".architecture-models" / ".architecture-model.yaml"
            if sos_file.exists():
                sos_model = _load_comp(sos_file)
                sos_result = compute_completeness(sos_model)
                response["sos_completeness"] = {
                    "score": sos_result.score,
                    "grade": sos_result.grade,
                    "dimensions": sos_result.dimensions,
                    "gaps": sos_result.gaps,
                }
        except Exception:
            pass  # non-fatal

        # Add scope info if scoped run
        if scope:
            response["scope"] = boundary.system_id
            response["system_name"] = boundary.name
            response["system_files"] = boundary.files

        # B2.2.5: snapshot every distinct component in the SIL store to YAML.
        # Best-effort — snapshot failures must not fail the pipeline call.
        try:
            _write_sil_snapshots(root)
        except Exception:
            pass

        # Phase 2 Task 19: append a DriftSnapshot to .architecture/drift.jsonl.
        # Fail-soft: journal is diagnostic. Uses a minimal, local drift
        # detector (orphan / unrealized_capability / broken_ref /
        # missing_impl) — a shared architecture_model.core.drift helper
        # is deferred; the primitives live here for Task 19.
        try:
            _append_drift_snapshot(root)
        except Exception:
            pass

        return response
    except Exception as e:
        import traceback

        return {"error": f"Pipeline failed: {e}", "traceback": traceback.format_exc()}


def _append_drift_snapshot(root: Path) -> None:
    """Compute drift flags from the emitted model and append a snapshot.

    Rules (minimal, deterministic, dependency-free):
        * ``broken_ref``: relationship endpoint (``from`` / ``to``) does
          not resolve to a known entity id.
        * ``unrealized_capability``: capability with no incoming
          ``realizes`` relationship.
        * ``orphan``: component appearing in NO relationship (either side).
        * ``missing_impl``: component with an empty ``files`` list.

    Silently returns if no model file exists at ``.architecture-model.yaml``.
    """
    from architecture_model.core.parser import load_model
    from architecture_model.feedback.drift import (
        DriftFlag,
        DriftSnapshot,
        append as _drift_append,
    )

    model_file = root / ".architecture-model.yaml"
    if not model_file.exists():
        return
    model = load_model(model_file)

    entity_ids: set[str] = set()
    for coll in (
        model.entities.components,
        model.entities.capabilities,
        model.entities.behaviors,
        model.entities.interfaces,
        model.entities.constraints,
        model.entities.actors,
        model.entities.layers,
    ):
        for e in coll:
            entity_ids.add(getattr(e, "id", ""))
    entity_ids.discard("")

    # Endpoints referenced by any relationship.
    referenced: set[str] = set()
    realizes_targets: set[str] = set()
    flags: list[DriftFlag] = []
    for rel in model.relationships:
        rel_from = getattr(rel, "from_id", "")
        rel_to = getattr(rel, "to_id", "")
        rel_type = getattr(rel, "type", "")
        referenced.add(rel_from)
        referenced.add(rel_to)
        for endpoint in (rel_from, rel_to):
            if endpoint and endpoint not in entity_ids:
                flags.append(
                    DriftFlag(
                        entity_id=endpoint,
                        kind="broken_ref",
                        detail=f"{rel_type}: unknown endpoint",
                    )
                )
        if rel_type == "realizes":
            realizes_targets.add(rel_to)

    for cap in model.entities.capabilities:
        if cap.id not in realizes_targets:
            flags.append(
                DriftFlag(
                    entity_id=cap.id,
                    kind="unrealized_capability",
                    detail="no realizing component",
                )
            )

    for comp in model.entities.components:
        if comp.id not in referenced:
            flags.append(
                DriftFlag(
                    entity_id=comp.id,
                    kind="orphan",
                    detail="no incoming or outgoing relationships",
                )
            )
        files = getattr(comp, "files", None) or []
        if not files:
            flags.append(
                DriftFlag(
                    entity_id=comp.id,
                    kind="missing_impl",
                    detail="component has no source files declared",
                )
            )

    # model revision: best-effort from meta.digest / schema_version; None if unknown.
    revision = getattr(model.meta, "digest", None) or getattr(
        model.meta, "schema_version", "unknown"
    )
    _drift_append(
        root,
        DriftSnapshot(model_revision=str(revision), flags=tuple(flags)),
    )
