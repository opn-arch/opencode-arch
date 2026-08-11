"""architect_pipeline MCP tool — run the 10-stage extraction pipeline.

Supports stage-by-stage execution with file-based cache persistence.
The MCP orchestrator calls this tool once per stage, reviews uncertainties,
resolves them via LLM, and passes resolutions on the next call.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from opencode_arch.mcp.quality import with_quality


@with_quality
async def run_pipeline(
    repo_path: str,
    stage: str = "",
    recursive: bool = True,
    resolutions: list[dict[str, Any]] | None = None,
    clear_cache: bool = False,
) -> dict[str, Any]:
    """Run the 10-stage extraction pipeline (stage-by-stage or all at once).

    Args:
        repo_path: Path to the repository root.
        stage: Run to specific stage (empty = all). One of:
            observe, infer, allocate, relate, specify, contract,
            validate, decompose, synthesize, emit.
        recursive: If True, synthesize stage runs scoped sub-pipelines
            for each detected system.
        resolutions: List of resolved uncertainties from the previous stage.
            Each dict: {category, resolution, confidence, source}.
            These are converted to Evidence and applied before running.
        clear_cache: If True, clear cached results before running.

    Returns:
        dict with stages_completed, current_stage, uncertainties_to_resolve,
        pipeline_report, lessons, artifacts_dir, llm_calls.
    """
    root = Path(repo_path).resolve()
    if not root.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}

    output_dir = root / ".architecture-models"
    cache_dir = root / ".architecture" / "pipeline-cache"
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

        # Initialize cache
        cache = PipelineCache(cache_dir)
        if clear_cache:
            cache.clear()

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
                ctx.llm_calls.append(LLMCallRecord(
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
                ))

        # Run pipeline
        if stage:
            results = coord.run_to(stage, ctx)
        else:
            results = coord.run_all(ctx)

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
                uncertainties_to_resolve.append({
                    "category": u.category,
                    "description": u.description,
                    "context": u.context,
                    "suggested_fallback": u.suggested_fallback,
                    "priority": u.priority,
                })

        # Generate report and lessons
        report = generate_pipeline_report(
            results, system_name=root.name, llm_calls=ctx.llm_calls
        )

        lesson_entries: list[LessonEntry] = []
        for name, result in results.items():
            lesson_entries.extend(
                LessonEntry.from_diagnostics(name, result.diagnostics)
            )
            lesson_entries.extend(
                LessonEntry.from_uncertainties(name, result.uncertainties)
            )
            stage_llm = [c for c in ctx.llm_calls if c.stage == name]
            lesson_entries.extend(LessonEntry.from_llm_calls(name, stage_llm))
        lessons = generate_lessons(lesson_entries, system_name=root.name)

        # LLM call summaries
        llm_summaries = []
        for call in ctx.llm_calls:
            llm_summaries.append({
                "stage": call.stage,
                "purpose": call.purpose,
                "tokens": call.total_tokens,
                "model": call.model,
                "cached": call.cached,
                "files_sent": call.files_sent,
            })

        # Record telemetry
        try:
            from opencode_arch.telemetry.collector import drain_and_store
            drain_and_store(tool="architect_pipeline", repo=root.name)
        except Exception:
            pass

        return {
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
        }
    except Exception as e:
        import traceback
        return {"error": f"Pipeline failed: {e}", "traceback": traceback.format_exc()}
