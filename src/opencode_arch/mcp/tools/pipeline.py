"""architect_pipeline MCP tool — run the 10-stage extraction pipeline."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from opencode_arch.mcp.quality import with_quality


@with_quality
async def run_pipeline(
    repo_path: str,
    stage: str = "",
    recursive: bool = True,
) -> dict[str, Any]:
    """Run the 10-stage extraction pipeline.

    Args:
        repo_path: Path to the repository root.
        stage: Run to specific stage (empty = all). One of:
            observe, infer, allocate, relate, specify, contract,
            validate, decompose, synthesize, emit.
        recursive: If True, synthesize stage runs scoped sub-pipelines
            for each detected system.

    Returns:
        dict with stages, pipeline_report, lessons, artifacts_dir, llm_calls.
    """
    root = Path(repo_path).resolve()
    if not root.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}

    output_dir = root / ".architecture-models"
    learning_path = root / ".architecture" / "learning"

    try:
        from architecture_model.pipeline import (
            PipelineCoordinator,
            PipelineContext,
            LearningStore,
            LessonEntry,
            generate_lessons,
            generate_pipeline_report,
        )
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

        # Run pipeline
        if stage:
            results = coord.run_to(stage, ctx)
        else:
            results = coord.run_all(ctx)

        # Build stage summaries
        stage_summaries = {}
        for name, result in results.items():
            stage_summaries[name] = {
                "score": result.quality.score,
                "duration_ms": result.duration_ms,
                "diagnostics": len(result.diagnostics),
                "uncertainties": len(result.uncertainties),
            }

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
            "stages": stage_summaries,
            "pipeline_report": report,
            "lessons": lessons,
            "artifacts_dir": str(output_dir),
            "llm_calls": llm_summaries,
            "total_llm_tokens": sum(c.total_tokens for c in ctx.llm_calls),
        }
    except Exception as e:
        return {"error": f"Pipeline failed: {e}"}
