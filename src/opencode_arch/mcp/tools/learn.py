"""architect_learn tool implementation."""
from __future__ import annotations

import json
from pathlib import Path

GLOBAL_LEARNING_PATH = Path.home() / ".config" / "opencode" / "arch-learning"


async def record_learning(
    learning_type: str,
    stage: str = "", condition: str = "", action: str = "",
    rationale: str = "", learned_from: str = "",
    name: str = "", indicators: str = "", problem: str = "", solution: str = "",
    trigger: str = "", diagnosis: str = "", fix_applied: str = "",
    validation: str = "", files_changed: str = "", commit: str = "",
    threshold_parameter: str = "", threshold_value: str = "",
    _learning_path: Path | None = None,
) -> str:
    """Record a learning (heuristic, archetype, or workflow) to the global store."""
    from architecture_model.pipeline.global_learning import (
        ArchetypePattern, GlobalLearningStore, HeuristicRule, WorkflowLesson,
    )
    store_path = _learning_path if _learning_path is not None else GLOBAL_LEARNING_PATH
    store = GlobalLearningStore(store_path)

    if learning_type == "heuristic":
        existing = store.get_heuristics()
        next_id = f"HR-{len(existing) + 1:03d}"
        threshold = {}
        if threshold_parameter:
            threshold = {"parameter": threshold_parameter, "value": float(threshold_value) if threshold_value else 0}
        store.add_heuristic(HeuristicRule(
            id=next_id, stage=stage, condition=condition,
            action=action, rationale=rationale, learned_from=learned_from,
            validated_on=[], threshold=threshold,
        ))
        return json.dumps({"status": "ok", "id": next_id, "message": f"Recorded heuristic: {condition} \u2192 {action}"})

    elif learning_type == "archetype":
        existing = store.get_archetypes()
        next_id = f"AP-{len(existing) + 1:03d}"
        store.add_archetype(ArchetypePattern(
            id=next_id, name=name,
            indicators=[i.strip() for i in indicators.split(",") if i.strip()],
            problem=problem, solution=solution, applicable_repos=[],
        ))
        return json.dumps({"status": "ok", "id": next_id, "message": f"Recorded archetype: {name}"})

    elif learning_type == "workflow":
        existing = store.get_workflows()
        next_id = f"WL-{len(existing) + 1:03d}"
        store.add_workflow(WorkflowLesson(
            id=next_id, trigger=trigger, diagnosis=diagnosis,
            fix_applied=fix_applied, validation=validation,
            files_changed=[f.strip() for f in files_changed.split(",") if f.strip()],
            commit=commit,
        ))
        return json.dumps({"status": "ok", "id": next_id, "message": f"Recorded workflow: {trigger}"})

    return json.dumps({"status": "error", "message": f"Unknown learning_type: {learning_type}. Use: heuristic, archetype, workflow"})
