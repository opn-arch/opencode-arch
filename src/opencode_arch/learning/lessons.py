"""Lesson extraction and storage.

Extracts insights from regen loop outcomes that can inform future runs.
Lessons are automatically derived from patterns and stored for retrieval.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Lesson:
    """A learned insight from regen loop experience."""
    lesson_id: str               # unique hash
    discovered_repo: str         # where it was first observed
    category: str                # "pattern", "optimization", "limitation", "success"
    description: str             # human-readable insight
    evidence: dict[str, Any] = field(default_factory=dict)


def _make_lesson_id(category: str, description: str) -> str:
    """Generate a stable lesson ID from content."""
    content = f"{category}:{description}"
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def extract_lessons(
    repo: str,
    mode: str,
    subsystem_results: dict[str, dict[str, Any]],
) -> list[Lesson]:
    """Extract lessons from a completed regen loop run.

    Looks for:
    - Correlation between features and convergence
    - Novel patterns not in taxonomy
    - Success patterns worth replicating
    - Limitations to document

    Args:
        repo: Repository name.
        mode: "normal" or "blind".
        subsystem_results: Results from run_regen_loop.

    Returns:
        List of lessons extracted.
    """
    lessons: list[Lesson] = []

    # Analyze convergence patterns
    converged_features: list[dict] = []
    failed_features: list[dict] = []

    for name, result in subsystem_results.items():
        features = result.get("features", {})
        if result.get("converged", False):
            converged_features.append(features)
        else:
            failed_features.append(features)

    # Lesson: Contract count threshold
    if converged_features and failed_features:
        avg_conv_contracts = sum(f.get("contract_count", 0) for f in converged_features) / len(converged_features)
        avg_fail_contracts = sum(f.get("contract_count", 0) for f in failed_features) / len(failed_features)

        if avg_conv_contracts > avg_fail_contracts * 2:
            desc = (f"Subsystems with >{int(avg_fail_contracts)} contracts converge "
                    f"({avg_conv_contracts:.0f} avg vs {avg_fail_contracts:.0f} avg)")
            lessons.append(Lesson(
                lesson_id=_make_lesson_id("pattern", desc),
                discovered_repo=repo,
                category="pattern",
                description=desc,
                evidence={
                    "avg_converged_contracts": avg_conv_contracts,
                    "avg_failed_contracts": avg_fail_contracts,
                    "mode": mode,
                },
            ))

    # Lesson: Signature count correlation
    if converged_features and failed_features:
        avg_conv_sigs = sum(f.get("signature_count", 0) for f in converged_features) / len(converged_features)
        avg_fail_sigs = sum(f.get("signature_count", 0) for f in failed_features) / len(failed_features)

        if avg_fail_sigs > avg_conv_sigs * 1.5:
            desc = (f"High signature count ({avg_fail_sigs:.0f}) correlates with failure — "
                    "complex modules need more context")
            lessons.append(Lesson(
                lesson_id=_make_lesson_id("limitation", desc),
                discovered_repo=repo,
                category="limitation",
                description=desc,
                evidence={
                    "avg_converged_signatures": avg_conv_sigs,
                    "avg_failed_signatures": avg_fail_sigs,
                },
            ))

    # Lesson: Perfect fidelity on simple subsystems
    simple_converged = [
        name for name, r in subsystem_results.items()
        if r.get("converged") and r.get("features", {}).get("signature_count", 0) < 10
    ]
    if len(simple_converged) >= 3:
        desc = f"Simple subsystems (<10 signatures) reliably converge: {', '.join(simple_converged[:5])}"
        lessons.append(Lesson(
            lesson_id=_make_lesson_id("success", desc),
            discovered_repo=repo,
            category="success",
            description=desc,
            evidence={"subsystems": simple_converged},
        ))

    # Lesson: All failures are same pattern (systemic issue)
    all_patterns: dict[str, int] = {}
    for r in subsystem_results.values():
        if not r.get("converged"):
            for pattern, count in r.get("failure_patterns", {}).items():
                all_patterns[pattern] = all_patterns.get(pattern, 0) + count

    if all_patterns:
        dominant = max(all_patterns, key=all_patterns.get)
        total_failures = sum(all_patterns.values())
        if all_patterns[dominant] / total_failures > 0.7:
            desc = (f"Dominant failure pattern '{dominant}' accounts for "
                    f"{all_patterns[dominant]}/{total_failures} failures — systemic issue")
            lessons.append(Lesson(
                lesson_id=_make_lesson_id("pattern", desc),
                discovered_repo=repo,
                category="pattern",
                description=desc,
                evidence={"pattern_distribution": all_patterns},
            ))

    return lessons
