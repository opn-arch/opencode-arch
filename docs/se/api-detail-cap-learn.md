# API Detail — CAP-LEARN: Learning Loop

## Overview

| Field | Value |
|-------|-------|
| ID | CAP-LEARN |
| F-Block | F3 (Intelligence) |
| Priority | Medium |
| Realized by | COMP-LEARNING (`learning/`) |
| Depends on | COMP-TELEMETRY |

---

## Pattern Classifier — `opencode_arch.learning.classifier`

### `classify_failures(test_output, pass_rate=0.0, total_tests=0, failed_tests=0) -> list[FailureClassification]`

Dual-level failure classifier. Combines regex matching (Level 1) with structured analysis (Level 2).

**Level 1 — Raw Regex (14 rules):**

| Pattern Type | Regex Signal | Confidence |
|-------------|-------------|------------|
| `CROSS_DEP` | `ImportError: cannot import name '...' from '...'` | 0.95 |
| `CROSS_DEP` | `ModuleNotFoundError: No module named '...'` | 0.8 |
| `CROSS_DEP` | `NameError: name '...' is not defined` | 0.6 |
| `MISSING_IMPL` | `AttributeError: module '...' has no attribute '...'` | 0.9 |
| `MISSING_IMPL` | `AttributeError: '...' object has no attribute '...'` | 0.9 |
| `WRONG_CONSTANT` | `AssertionError: assert "..." == "..."` | 0.85 |
| `WRONG_CONSTANT` | `AssertionError: assert N == M` | 0.85 |
| `API_MISMATCH` | `TypeError: f() takes N positional argument` | 0.9 |
| `API_MISMATCH` | `TypeError: f() got an unexpected keyword argument` | 0.9 |
| `API_MISMATCH` | `TypeError: f() missing N required positional` | 0.9 |
| `TEST_INFRA` | `ModuleNotFoundError: No module named 'tests.'` | 0.95 |
| `TEST_INFRA` | `ImportError: cannot import name ... from 'tests.'` | 0.9 |

**Level 2 — Structured Analysis:**

- `COMPLEX_BEHAVIOR`: >5 failures AND pass_rate < 50% → many behavioral issues
- `CROSS_DEP` (systemic): ≥80% of failures are import errors → single root cause

**Returns:** `list[FailureClassification]`, each with:
- `pattern: PatternType` — one of 7 types
- `confidence: float` — 0.0-1.0
- `raw_signal: str` — matched text
- `structured_signal: dict` — parsed details
- `suggested_strategy: Strategy` — what to do about it
- `affected_symbols: list[str]` — specific identifiers involved

---

## Adaptive Prompt Optimizer — `opencode_arch.learning.adapter`

### `get_adaptations(subsystem_name, dependency_count, signature_count, contract_count, body_hint_coverage, historical_patterns=None) -> list[PromptAdaptation]`

Determines prompt adaptations BEFORE the first attempt based on subsystem characteristics and historical patterns.

**4 Heuristic Rules:**

| Rule | Condition | Strategy | Effect |
|------|-----------|----------|--------|
| 1 | `dependency_count >= 3` | `EXPAND_DEP_CONTEXT` | Include body_hints for upstream modules |
| 2 | `contract_count < 10` | `INCREASE_CONTRACT_CAP` | Raise contract cap to 200 |
| 3 | `body_hint_coverage < 50%` AND `signature_count > 5` | `INCLUDE_SOURCE_EXCERPT` | Flag need for source excerpts |
| 4 | Historical `cross_dep >= 2` | `EXPAND_DEP_CONTEXT` | Proactive dep expansion |

### `PromptAdaptation` (dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `strategy` | `Strategy` | Which strategy to apply |
| `reason` | `str` | Why this adaptation was chosen |
| `params` | `dict` | Strategy-specific parameters |

---

## Report Card Assessor — `opencode_arch.learning.assessor`

### `generate_report_card(...) -> ReportCard`

Self-assessment after each regen loop run.

### `ReportCard` (dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `repo` | `str` | Repository name |
| `mode` | `str` | "normal" or "blind" |
| `fidelity` | `float` | converged/total (0.0-1.0) |
| `compression_ratio` | `float` | source_equiv / prompt_tokens |
| `time_per_subsystem` | `float` | Average seconds |
| `total_subsystems` | `int` | How many subsystems |
| `converged_subsystems` | `int` | How many passed all tests |
| `fidelity_trend` | `str` | "UP", "DOWN", "STABLE" |
| `compression_trend` | `str` | "UP", "DOWN", "STABLE" |
| `failure_patterns` | `dict[str, int]` | Pattern type → count |
| `novel_patterns` | `int` | Unclassified failures |
| `grade` | `str` | A through F |
| `improvement_actions` | `list[str]` | Actionable suggestions |

### Grading Formula

| Grade | Criteria |
|-------|----------|
| A | ≥90% fidelity, ≥5x compression, 0 novel patterns |
| B | ≥75% fidelity, ≥3x compression |
| C | ≥60% fidelity |
| D | ≥40% fidelity |
| F | <40% fidelity |

---

## Lesson Extractor — `opencode_arch.learning.lessons`

Extracts reusable insights from regen outcomes. Stores with content-hashed IDs for deduplication.

Lesson categories: contract thresholds, signature correlations, dominant patterns, systemic issues.

---

## Doc Drift Maintainer — `opencode_arch.learning.maintainer`

Performs 4 checks on project documentation:
1. Test count (docs match actual)
2. Version sync (pyproject.toml matches docs)
3. Schema version (model matches code)
4. Python version requirement

Auto-fixes simple cases (version numbers, test counts). Records unresolvable drift flags to telemetry.
