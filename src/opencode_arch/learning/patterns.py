"""Failure pattern definitions and taxonomy."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PatternType(str, Enum):
    """Known failure pattern types."""
    CROSS_DEP = "cross_dep"           # ImportError/NameError from another module
    MISSING_IMPL = "missing_impl"     # AttributeError on generated code
    WRONG_CONSTANT = "wrong_constant" # AssertionError with literal mismatch
    API_MISMATCH = "api_mismatch"     # TypeError wrong arg count/types
    COMPLEX_BEHAVIOR = "complex_behavior"  # Multiple sequential failures
    TEST_INFRA = "test_infra"         # ModuleNotFoundError for test helpers
    UNKNOWN = "unknown"               # Unclassified


class Strategy(str, Enum):
    """Adaptation strategies to apply for each pattern."""
    EXPAND_DEP_CONTEXT = "expand_dep_context"       # Include full dep API + body_hints
    INCLUDE_SOURCE_EXCERPT = "include_source_excerpt"  # Escape hatch: include source
    PRIORITIZE_CONSTANTS = "prioritize_constants"    # Move constants to top, increase budget
    FIX_SIGNATURES = "fix_signatures"               # Include exact param lists
    INCREASE_CONTRACT_CAP = "increase_contract_cap"  # Raise from 50 to 100+
    COPY_TEST_INFRA = "copy_test_infra"             # Additional test helper copying
    NO_ACTION = "no_action"                         # Pattern recognized but no fix available


@dataclass
class FailureClassification:
    """A classified test failure with dual-level signals."""
    pattern: PatternType
    confidence: float                    # 0.0-1.0
    raw_signal: str                      # regex match from pytest output
    structured_signal: dict = field(default_factory=dict)  # parsed details
    suggested_strategy: Strategy = Strategy.NO_ACTION
    affected_symbols: list[str] = field(default_factory=list)  # symbols/modules involved
    source_module: str = ""              # which module the failure relates to


# Pattern → Strategy mapping (default strategies)
PATTERN_STRATEGIES: dict[PatternType, Strategy] = {
    PatternType.CROSS_DEP: Strategy.EXPAND_DEP_CONTEXT,
    PatternType.MISSING_IMPL: Strategy.INCLUDE_SOURCE_EXCERPT,
    PatternType.WRONG_CONSTANT: Strategy.PRIORITIZE_CONSTANTS,
    PatternType.API_MISMATCH: Strategy.FIX_SIGNATURES,
    PatternType.COMPLEX_BEHAVIOR: Strategy.INCREASE_CONTRACT_CAP,
    PatternType.TEST_INFRA: Strategy.COPY_TEST_INFRA,
    PatternType.UNKNOWN: Strategy.NO_ACTION,
}
