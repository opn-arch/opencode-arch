"""architect_gate MCP tool — check development gate readiness."""

from __future__ import annotations

from pathlib import Path
from typing import Any


async def check_gate(repo_path: str, model_yaml: str = "") -> dict[str, Any]:
    """Check development gate for an architecture model against code reality.

    Args:
        repo_path: Absolute path to the repository root.
        model_yaml: Optional YAML string. If empty, reads .architecture-model.yaml.

    Returns:
        Dict with lifecycle_phase, sub-scores, phase_requirements_met, and issues.
    """
    repo = Path(repo_path)
    if not repo.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}

    try:
        from architecture_model.authoring.gate import check_development_gate
        from architecture_model.core.parser import load_model
        from architecture_model.manifest.generator import generate_manifest

        # Load model
        if model_yaml:
            import yaml
            from architecture_model.core.parser import ArchitectureModel

            # Use load_model-compatible path: write temp then load, or parse directly
            from architecture_model.core.parser import _parse_raw

            raw = yaml.safe_load(model_yaml)
            model = _parse_raw(raw)
        else:
            model_path = repo / ".architecture-model.yaml"
            if not model_path.exists():
                return {"error": f"No model found at {model_path} and no model_yaml provided"}
            model = load_model(model_path)

        # Generate manifest
        manifest = generate_manifest(repo)

        # Determine phase
        phase = None
        if hasattr(model.meta, "lifecycle_phase"):
            phase = model.meta.lifecycle_phase

        # Run gate check
        result = check_development_gate(model, manifest, phase=phase)

        result = {
            "lifecycle_phase": result.phase,
            "capability_realization": result.capability_realization,
            "constraint_allocation": result.constraint_allocation,
            "file_coverage": result.file_coverage,
            "overall": result.overall,
            "phase_requirements_met": result.phase_requirements_met,
            "issues": result.issues,
        }

        # Auto-trigger live assessment and workspace evaluation
        try:
            from .assess import assess_conversation
            from .evaluate import evaluate_workspace

            assess_result = await assess_conversation(
                repo_path, conversation_text=f"Gate check completed for {repo_path}"
            )
            eval_result = await evaluate_workspace(repo_path)

            result["live_assessment"] = {
                "findings_count": assess_result.get("findings_count", 0),
                "cross_repo_impacts": assess_result.get("cross_repo_impacts", 0),
            }
            result["workspace_health"] = eval_result.get("overall_health")
            result["recommendations"] = eval_result.get("recommendations", [])
        except Exception:
            pass  # Don't let assessment failure block gate

        # Regen readiness recommendation
        try:
            from architecture_model.core.regen_readiness import compute_regen_readiness

            regen = compute_regen_readiness(model)
            if regen.overall < 50:
                result["recommendations"] = result.get("recommendations", [])
                result["recommendations"].append(
                    f"Regen readiness is {regen.grade} ({regen.overall:.0f}%). "
                    "Consider running enrichment before proceeding — model lacks detail for reliable code generation."
                )
            result["regen_grade"] = regen.grade
            result["regen_score"] = round(regen.overall, 1)
        except Exception:
            pass

        # Completeness grade
        try:
            from architecture_model.core.completeness import compute_completeness

            completeness = compute_completeness(model)
            result["completeness_grade"] = completeness.grade
            result["completeness_score"] = round(completeness.score, 1)
            result["completeness_gaps"] = completeness.gaps
            result["completeness_dimensions"] = {
                k: round(v, 1) for k, v in completeness.dimensions.items()
            }
            if completeness.grade in ("D", "F"):
                result["recommendations"] = result.get("recommendations", [])
                result["recommendations"].append(
                    f"Completeness is {completeness.grade} ({completeness.score:.0f}%). "
                    "Model captures structure but not behavior — run enriched pipeline to auto-derive behaviors, interfaces, and requirements."
                )
        except Exception:
            pass

        # Auto-log prompt: remind to log progress
        result["next_steps"] = [
            "ALWAYS call architect_log after completing implementation tasks",
            "Call architect_log after git commits to record progress",
            "Call architect_log when discovering architectural decisions",
        ]

        # Phase 2 Task 18: append gate outcome to .architecture/gates.jsonl.
        # Fail-soft: the journal is diagnostic — never fail the gate on
        # write errors. model_revision is left None (optional) — a real
        # revision lookup would require ArchitecturePackage.from_repo which
        # is not currently a public API on ArchitecturePackage.
        try:
            from architecture_model.feedback.gates import GateEvent, append as _gates_append

            outcome = "pass" if result.get("phase_requirements_met") else "fail"
            findings = tuple(str(i) for i in (result.get("issues") or ()))
            _gates_append(
                repo,
                GateEvent(
                    gate_id="architect_gate",
                    outcome=outcome,  # type: ignore[arg-type]
                    findings=findings,
                    model_revision=None,
                ),
            )
        except Exception:
            # Journal is best-effort; never propagate.
            pass

        return result
    except Exception as e:
        return {"error": f"Gate check failed: {e}"}
