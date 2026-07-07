"""Adaptive prompt optimization based on classified failure patterns.

Queries historical telemetry for similar subsystems and applies learned
strategies to modify prompt construction BEFORE the first attempt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from opencode_arch.learning.patterns import (
    FailureClassification,
    PatternType,
    Strategy,
)


@dataclass
class PromptAdaptation:
    """A specific adaptation to apply to prompt construction."""
    strategy: Strategy
    reason: str                          # why this adaptation is being applied
    params: dict[str, Any] = field(default_factory=dict)
    # params vary by strategy:
    # EXPAND_DEP_CONTEXT: {"dep_modules": ["_base", "_config"], "include_body_hints": True}
    # INCLUDE_SOURCE_EXCERPT: {"functions": ["complex_func"]}
    # PRIORITIZE_CONSTANTS: {"boost_factor": 2.0}
    # FIX_SIGNATURES: {"symbols": ["MyClass.method"]}
    # INCREASE_CONTRACT_CAP: {"new_cap": 100}


def get_adaptations(
    subsystem_name: str,
    dependency_count: int,
    signature_count: int,
    contract_count: int,
    body_hint_coverage: float,
    historical_patterns: list[dict[str, Any]] | None = None,
) -> list[PromptAdaptation]:
    """Determine prompt adaptations based on subsystem characteristics and history.

    This is called BEFORE the first prompt attempt to proactively adjust
    based on what we've learned from previous repos.

    Args:
        subsystem_name: Name of the current subsystem.
        dependency_count: Number of upstream dependencies.
        signature_count: Number of function signatures in model.
        contract_count: Number of test contracts available.
        body_hint_coverage: Fraction of functions with body_hints (0.0-1.0).
        historical_patterns: Past failure patterns from telemetry for similar subsystems.

    Returns:
        List of adaptations to apply to prompt construction.
    """
    adaptations: list[PromptAdaptation] = []

    # Rule 1: High dependency count → expand dep context proactively
    if dependency_count >= 3:
        adaptations.append(PromptAdaptation(
            strategy=Strategy.EXPAND_DEP_CONTEXT,
            reason=f"Subsystem has {dependency_count} dependencies (threshold: 3)",
            params={"include_body_hints": True},
        ))

    # Rule 2: Low contract count → increase cap and prioritize what we have
    if contract_count < 10:
        adaptations.append(PromptAdaptation(
            strategy=Strategy.INCREASE_CONTRACT_CAP,
            reason=f"Only {contract_count} contracts available (low coverage)",
            params={"new_cap": 200},  # Don't cap at all for low-contract subsystems
        ))

    # Rule 3: Low body_hint coverage → likely to fail on implementation details
    if body_hint_coverage < 0.5 and signature_count > 5:
        adaptations.append(PromptAdaptation(
            strategy=Strategy.INCLUDE_SOURCE_EXCERPT,
            reason=f"Body hint coverage is {body_hint_coverage:.0%} (threshold: 50%)",
            params={"coverage_threshold": body_hint_coverage},
        ))

    # Rule 4: Historical patterns suggest specific strategies
    if historical_patterns:
        pattern_counts: dict[str, int] = {}
        for entry in historical_patterns:
            pattern = entry.get("pattern", "")
            if pattern:
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        # If cross_dep failures dominate history for similar subsystems
        if pattern_counts.get("cross_dep", 0) >= 2:
            if not any(a.strategy == Strategy.EXPAND_DEP_CONTEXT for a in adaptations):
                adaptations.append(PromptAdaptation(
                    strategy=Strategy.EXPAND_DEP_CONTEXT,
                    reason=f"Historical: {pattern_counts['cross_dep']} cross-dep failures in similar subsystems",
                    params={"include_body_hints": True, "historical": True},
                ))

        # If wrong_constant failures are common
        if pattern_counts.get("wrong_constant", 0) >= 2:
            adaptations.append(PromptAdaptation(
                strategy=Strategy.PRIORITIZE_CONSTANTS,
                reason=f"Historical: {pattern_counts['wrong_constant']} constant mismatches in similar subsystems",
                params={"boost_factor": 2.0},
            ))

    return adaptations


def apply_adaptations(
    adaptations: list[PromptAdaptation],
    contract_cap: int = 50,
    include_dep_body_hints: bool = False,
) -> dict[str, Any]:
    """Apply adaptations and return modified prompt parameters.

    Returns a dict of overrides to pass to _build_prompt:
    - contract_cap: int (max contracts to include)
    - include_dep_body_hints: bool (include body_hints in dep context)
    - extra_context: str (additional context to append)
    - source_excerpts: list[str] (functions needing full source)
    """
    result: dict[str, Any] = {
        "contract_cap": contract_cap,
        "include_dep_body_hints": include_dep_body_hints,
        "extra_context": "",
        "source_excerpts": [],
        "adaptations_applied": [],
    }

    for adaptation in adaptations:
        result["adaptations_applied"].append(
            f"{adaptation.strategy.value}: {adaptation.reason}"
        )

        if adaptation.strategy == Strategy.EXPAND_DEP_CONTEXT:
            result["include_dep_body_hints"] = True

        elif adaptation.strategy == Strategy.INCREASE_CONTRACT_CAP:
            new_cap = adaptation.params.get("new_cap", 100)
            result["contract_cap"] = max(result["contract_cap"], new_cap)

        elif adaptation.strategy == Strategy.INCLUDE_SOURCE_EXCERPT:
            functions = adaptation.params.get("functions", [])
            result["source_excerpts"].extend(functions)

        elif adaptation.strategy == Strategy.PRIORITIZE_CONSTANTS:
            # Signal to put constants section BEFORE signatures in prompt
            result["extra_context"] += "\n# NOTE: Constants are critical for this subsystem — use exact values.\n"

        elif adaptation.strategy == Strategy.FIX_SIGNATURES:
            symbols = adaptation.params.get("symbols", [])
            if symbols:
                result["extra_context"] += f"\n# IMPORTANT: Match exact signatures for: {', '.join(symbols)}\n"

    return result
