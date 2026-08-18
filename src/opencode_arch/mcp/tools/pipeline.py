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
            Each dict: {category, resolution, confidence, source}.
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
            for res in resolutions:
                ev = Evidence(
                    source=res.get("source", "llm_analysis"),
                    confidence=res.get("confidence", 0.8),
                    raw=res.get("resolution", ""),
                    location=res.get("category", ""),
                )
                ctx.prior_corrections.append(ev)

                # Record LLM call for each resolution
                ctx.llm_calls.append(
                    LLMCallRecord(
                        stage=res.get("for_stage", stage or "unknown"),
                        purpose=f"resolve uncertainty: {res.get('category', 'unknown')}",
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
            "hint": "Use architect_log to record decisions made during this stage.",
        }

        # Add scope info if scoped run
        if scope:
            response["scope"] = boundary.system_id
            response["system_name"] = boundary.name
            response["system_files"] = boundary.files

        return response
    except Exception as e:
        import traceback

        return {"error": f"Pipeline failed: {e}", "traceback": traceback.format_exc()}
