"""Report card generation and grading for regen loop runs.

Produces a self-assessment after each repo run: grade (A-F),
trending metrics, failure pattern breakdown, and improvement actions.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReportCard:
    """Self-assessment report for a regen loop run."""
    repo: str
    mode: str  # "normal" or "blind"

    # Core metrics
    fidelity: float              # converged/total (0.0-1.0)
    compression_ratio: float     # source_equiv / prompt_tokens
    time_per_subsystem: float    # avg seconds
    total_subsystems: int
    converged_subsystems: int

    # Trend (vs previous)
    fidelity_trend: str = "STABLE"       # "UP", "DOWN", "STABLE"
    compression_trend: str = "STABLE"

    # Pattern breakdown
    failure_patterns: dict[str, int] = field(default_factory=dict)
    novel_patterns: int = 0

    # Grade + actions
    grade: str = "C"
    improvement_actions: list[str] = field(default_factory=list)


def _compute_grade(fidelity: float, compression_ratio: float, novel_patterns: int) -> str:
    """Compute letter grade from metrics.

    A: >90% fidelity, compression >5x, 0 novel patterns
    B: >75% fidelity, compression >3x
    C: >60% fidelity
    D: >40% fidelity
    F: <40% fidelity
    """
    if fidelity >= 0.9 and compression_ratio >= 5.0 and novel_patterns == 0:
        return "A"
    elif fidelity >= 0.75 and compression_ratio >= 3.0:
        return "B"
    elif fidelity >= 0.6:
        return "C"
    elif fidelity >= 0.4:
        return "D"
    else:
        return "F"


def _compute_trend(current: float, previous: float | None) -> str:
    """Determine trend direction."""
    if previous is None:
        return "STABLE"
    diff = current - previous
    if diff > 0.05:
        return "UP"
    elif diff < -0.05:
        return "DOWN"
    return "STABLE"


def _compute_improvement_actions(
    fidelity: float,
    compression_ratio: float,
    failure_patterns: dict[str, int],
    novel_patterns: int,
) -> list[str]:
    """Generate actionable improvement suggestions."""
    actions = []

    if fidelity < 0.7:
        dominant_pattern = max(failure_patterns, key=failure_patterns.get) if failure_patterns else None
        if dominant_pattern == "cross_dep":
            actions.append("Expand dependency context: include body_hints for upstream modules")
        elif dominant_pattern == "missing_impl":
            actions.append("Increase body_hint detail level for complex functions")
        elif dominant_pattern == "wrong_constant":
            actions.append("Verify constant extraction captures all test-expected values")
        else:
            actions.append(f"Investigate dominant failure pattern: {dominant_pattern}")

    if compression_ratio < 3.0:
        actions.append("Model is not providing enough compression — review token allocation")

    if novel_patterns > 0:
        actions.append(f"Classify {novel_patterns} novel failure patterns and add to taxonomy")

    if fidelity >= 0.9 and compression_ratio >= 5.0:
        actions.append("System performing well — consider adding a new benchmark repo")

    return actions


def generate_report_card(
    repo: str,
    mode: str,
    subsystem_results: dict[str, dict[str, Any]],
    previous_fidelity: float | None = None,
    previous_compression: float | None = None,
) -> ReportCard:
    """Generate a report card from regen loop results.

    Args:
        repo: Repository name.
        mode: "normal" or "blind".
        subsystem_results: Dict of {subsystem_name: result_dict} from run_regen_loop.
        previous_fidelity: Fidelity from previous repo (for trend).
        previous_compression: Compression from previous repo (for trend).

    Returns:
        ReportCard with grade, trends, and improvement actions.
    """
    total = len(subsystem_results)
    converged = sum(1 for r in subsystem_results.values() if r.get("converged", False))
    fidelity = converged / total if total > 0 else 0.0

    # Compute avg compression from token metrics
    compressions = []
    times = []
    for r in subsystem_results.values():
        metrics = r.get("token_metrics", {})
        if metrics.get("compression_ratio", 0) > 0:
            compressions.append(metrics["compression_ratio"])
        times.append(r.get("time_seconds", 0))

    avg_compression = sum(compressions) / len(compressions) if compressions else 0.0
    avg_time = sum(times) / len(times) if times else 0.0

    # Aggregate failure patterns from classifications
    failure_patterns: dict[str, int] = {}
    novel = 0
    for r in subsystem_results.values():
        patterns = r.get("failure_patterns", {})
        for pattern, count in patterns.items():
            if pattern == "unknown":
                novel += count
            else:
                failure_patterns[pattern] = failure_patterns.get(pattern, 0) + count

    # Compute grade and trends
    grade = _compute_grade(fidelity, avg_compression, novel)
    fidelity_trend = _compute_trend(fidelity, previous_fidelity)
    compression_trend = _compute_trend(avg_compression, previous_compression)
    actions = _compute_improvement_actions(fidelity, avg_compression, failure_patterns, novel)

    return ReportCard(
        repo=repo,
        mode=mode,
        fidelity=fidelity,
        compression_ratio=avg_compression,
        time_per_subsystem=avg_time,
        total_subsystems=total,
        converged_subsystems=converged,
        fidelity_trend=fidelity_trend,
        compression_trend=compression_trend,
        failure_patterns=failure_patterns,
        novel_patterns=novel,
        grade=grade,
        improvement_actions=actions,
    )
