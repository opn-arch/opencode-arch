"""Self-healing loop for spot-check failures.

When a spot-check fails, classifies the failure pattern, applies adaptive fixes
to the model context, and retries. Feeds outcomes into the learning store.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .spot_check import SpotCheckDiagnostic, SpotCheckResult


@dataclass
class HealAction:
    """An action taken to heal a failure."""
    pattern: str  # MISSING_IMPL, WRONG_CONSTANT, etc.
    action: str  # expand_context, add_body_hint, add_constant, increase_contracts
    target: str  # component or function name
    applied: bool = False


def classify_failure(diagnostics: list[SpotCheckDiagnostic]) -> list[HealAction]:
    """Classify failure diagnostics into actionable heal actions."""
    actions: list[HealAction] = []
    
    for d in diagnostics:
        if d.category == "MISSING_IMPL":
            actions.append(HealAction(
                pattern="MISSING_IMPL",
                action="add_body_hint",
                target=d.function_name or "unknown",
            ))
        elif d.category == "WRONG_CONSTANT":
            actions.append(HealAction(
                pattern="WRONG_CONSTANT",
                action="add_constant",
                target=d.function_name or "unknown",
            ))
        elif d.category == "CROSS_DEP":
            actions.append(HealAction(
                pattern="CROSS_DEP",
                action="expand_context",
                target=d.function_name or "unknown",
            ))
        elif d.category == "API_MISMATCH":
            actions.append(HealAction(
                pattern="API_MISMATCH",
                action="fix_signatures",
                target=d.function_name or "unknown",
            ))
    
    return actions


async def self_heal(
    result: SpotCheckResult,
    repo_path: Path,
    *,
    learning_store: Any = None,
) -> list[HealAction]:
    """Analyze a failed spot-check and produce healing actions.
    
    Records outcomes in learning store for cross-session improvement.
    """
    actions = classify_failure(result.diagnostics)
    
    # Record in learning store
    if learning_store:
        for action in actions:
            learning_store.add_resolution_outcome(
                category=action.pattern,
                description=f"{action.action} for {action.target}",
                method="spot_check",
            )
    
    return actions
