"""Dual-level failure pattern classifier.

Level 1 (Raw): Regex matching on pytest output text
Level 2 (Structured): Parsed test results cross-referenced with model data
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from opencode_arch.learning.patterns import (
    FailureClassification,
    PatternType,
    Strategy,
    PATTERN_STRATEGIES,
)


# --- Level 1: Raw regex patterns ---

_RAW_PATTERNS: list[tuple[str, PatternType, float]] = [
    # CROSS_DEP: ImportError from project module
    (r"ImportError: cannot import name '(\w+)' from '([^']+)'", PatternType.CROSS_DEP, 0.95),
    (r"ModuleNotFoundError: No module named '(\w[\w.]*)'", PatternType.CROSS_DEP, 0.8),
    (r"NameError: name '(\w+)' is not defined", PatternType.CROSS_DEP, 0.6),

    # MISSING_IMPL: AttributeError on generated code
    (r"AttributeError: (?:module |type object )?'(\w+)' has no attribute '(\w+)'", PatternType.MISSING_IMPL, 0.9),
    (r"AttributeError: '(\w+)' object has no attribute '(\w+)'", PatternType.MISSING_IMPL, 0.9),

    # WRONG_CONSTANT: Assertion with literal values
    (r"AssertionError: assert ['\"](.+)['\"] == ['\"](.+)['\"]", PatternType.WRONG_CONSTANT, 0.85),
    (r"AssertionError: assert (\d+) == (\d+)", PatternType.WRONG_CONSTANT, 0.85),
    (r"AssertionError: (?:assert )?(.+) != (.+)", PatternType.WRONG_CONSTANT, 0.7),

    # API_MISMATCH: Wrong number of arguments
    (r"TypeError: (\w+)\(\) takes (\d+) positional argument", PatternType.API_MISMATCH, 0.9),
    (r"TypeError: (\w+)\(\) got an unexpected keyword argument '(\w+)'", PatternType.API_MISMATCH, 0.9),
    (r"TypeError: (\w+)\(\) missing (\d+) required positional", PatternType.API_MISMATCH, 0.9),

    # TEST_INFRA: Test helper imports failing
    (r"ModuleNotFoundError: No module named 'tests\.", PatternType.TEST_INFRA, 0.95),
    (r"ModuleNotFoundError: No module named 'conftest'", PatternType.TEST_INFRA, 0.95),
    (r"ImportError: cannot import name .+ from 'tests\.", PatternType.TEST_INFRA, 0.9),
]


def _classify_raw(test_output: str) -> list[FailureClassification]:
    """Level 1: Classify failures from raw pytest output using regex."""
    classifications: list[FailureClassification] = []
    seen_patterns: set[tuple[PatternType, str]] = set()

    for regex, pattern_type, confidence in _RAW_PATTERNS:
        for match in re.finditer(regex, test_output):
            # Deduplicate: same pattern + same primary symbol
            key = (pattern_type, match.group(1) if match.groups() else "")
            if key in seen_patterns:
                continue
            seen_patterns.add(key)

            # Extract affected symbols
            symbols = [g for g in match.groups() if g]

            classifications.append(FailureClassification(
                pattern=pattern_type,
                confidence=confidence,
                raw_signal=match.group(0),
                structured_signal={"groups": symbols, "regex": regex},
                suggested_strategy=PATTERN_STRATEGIES[pattern_type],
                affected_symbols=symbols,
            ))

    return classifications


def _classify_structured(
    test_output: str,
    pass_rate: float,
    total_tests: int,
    failed_tests: int,
) -> list[FailureClassification]:
    """Level 2: Structured classification from parsed test results."""
    classifications: list[FailureClassification] = []

    # COMPLEX_BEHAVIOR: Many failures in same test module suggest behavioral complexity
    if failed_tests > 5 and pass_rate < 0.5:
        classifications.append(FailureClassification(
            pattern=PatternType.COMPLEX_BEHAVIOR,
            confidence=0.7,
            raw_signal=f"{failed_tests}/{total_tests} tests failed (pass_rate={pass_rate:.0%})",
            structured_signal={
                "failed_count": failed_tests,
                "total_count": total_tests,
                "pass_rate": pass_rate,
            },
            suggested_strategy=Strategy.INCREASE_CONTRACT_CAP,
        ))

    # If ALL tests fail with import errors, it's likely a single root cause
    import_errors = len(re.findall(r"(?:Import|Module)Error", test_output))
    if import_errors > 0 and import_errors >= failed_tests * 0.8:
        # Most failures are import-related — likely a single cross-dep issue
        classifications.append(FailureClassification(
            pattern=PatternType.CROSS_DEP,
            confidence=0.9,
            raw_signal=f"{import_errors} import errors out of {failed_tests} failures",
            structured_signal={"import_error_ratio": import_errors / max(failed_tests, 1)},
            suggested_strategy=Strategy.EXPAND_DEP_CONTEXT,
        ))

    return classifications


def classify_failures(
    test_output: str,
    pass_rate: float = 0.0,
    total_tests: int = 0,
    failed_tests: int = 0,
) -> list[FailureClassification]:
    """Classify test failures using both raw and structured analysis.

    Args:
        test_output: Raw pytest stdout/stderr text.
        pass_rate: Overall pass rate (0.0-1.0).
        total_tests: Total number of tests run.
        failed_tests: Number of failed tests.

    Returns:
        List of classified failures, sorted by confidence (highest first).
    """
    raw_results = _classify_raw(test_output)
    structured_results = _classify_structured(test_output, pass_rate, total_tests, failed_tests)

    # Merge: structured adds context but don't duplicate pattern types
    raw_patterns = {c.pattern for c in raw_results}
    merged = list(raw_results)
    for sc in structured_results:
        if sc.pattern not in raw_patterns:
            merged.append(sc)

    # Sort by confidence descending
    merged.sort(key=lambda c: c.confidence, reverse=True)
    return merged
