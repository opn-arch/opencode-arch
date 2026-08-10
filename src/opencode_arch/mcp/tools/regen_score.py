"""MCP tools for regen readiness scoring and spot-checking."""
from __future__ import annotations

from pathlib import Path


async def regen_score(*, repo_path: str, component_id: str = "") -> dict:
    """Compute regen readiness score for a repository or specific component.
    
    Returns overall score, grade, per-component breakdown, and blockers.
    """
    from architecture_model.core.parser import load_model
    from architecture_model.core.regen_readiness import (
        compute_regen_readiness,
        compute_component_readiness,
    )
    
    path = Path(repo_path)
    model_path = path / ".architecture-model.yaml"
    if not model_path.exists():
        return {"error": f"No model found at {model_path}"}
    
    model = load_model(model_path)
    
    if component_id:
        comp = next((c for c in model.entities.components if c.id == component_id), None)
        if not comp:
            return {"error": f"Component {component_id} not found"}
        readiness = compute_component_readiness(comp)
        return {
            "component_id": readiness.id,
            "name": readiness.name,
            "score": readiness.score,
            "grade": _grade(readiness.score),
            "body_hint_coverage": readiness.body_hint_coverage,
            "test_contract_count": readiness.test_contract_count,
            "constant_coverage": readiness.constant_coverage,
            "blockers": readiness.blockers,
            "functions": [
                {"name": f.name, "score": f.score, "quality": f.body_hint_quality, "blockers": f.blockers}
                for f in readiness.functions
            ],
        }
    
    readiness = compute_regen_readiness(model)
    return {
        "overall": readiness.overall,
        "grade": readiness.grade,
        "recommendation": readiness.recommendation,
        "blockers": readiness.blockers,
        "components": [
            {"id": c.id, "name": c.name, "score": c.score, "grade": _grade(c.score)}
            for c in readiness.components
        ],
    }


async def spot_check(
    *,
    repo_path: str,
    component_id: str = "",
    subsystem_id: str = "",
) -> dict:
    """Run a spot-check regeneration probe on a component or subsystem.
    
    Regenerates code via LLM, compares against source, reports diagnostics.
    On failure, classifies patterns and suggests healing actions.
    """
    from opencode_arch.regen.spot_check import select_target, run_spot_check
    from opencode_arch.regen.self_heal import classify_failure

    path = Path(repo_path)
    
    target = await select_target(
        path,
        component_id=component_id or None,
        subsystem_id=subsystem_id or None,
    )
    
    result = await run_spot_check(target, path)
    
    output = {
        "target": {
            "component_id": target.component_id,
            "subsystem_id": target.subsystem_id,
            "file_count": len(target.files),
        },
        "success": result.success,
        "match_percent": result.match_percent,
        "iterations": result.iterations,
        "diagnostics": [
            {"category": d.category, "severity": d.severity, "message": d.message, "suggestion": d.suggestion}
            for d in result.diagnostics
        ],
    }
    
    if not result.success:
        actions = classify_failure(result.diagnostics)
        output["heal_actions"] = [
            {"pattern": a.pattern, "action": a.action, "target": a.target}
            for a in actions
        ]
    
    return output


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 70:
        return "B"
    if score >= 50:
        return "C"
    if score >= 30:
        return "D"
    return "F"
