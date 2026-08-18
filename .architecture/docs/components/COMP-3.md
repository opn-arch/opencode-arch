# Component: CLI Commands (COMP-3)

**Status:** Status.ACTIVE
**Description:** Source in src/opencode_arch/cli (13 files)

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/cli/bench.py` | — | — |
| `src/opencode_arch/cli/calibrate.py` | — | — |
| `src/opencode_arch/cli/confidence.py` | — | — |
| `src/opencode_arch/cli/docs.py` | — | — |
| `src/opencode_arch/cli/docs_validator.py` | — | — |
| `src/opencode_arch/cli/export_data.py` | — | — |
| `src/opencode_arch/cli/extract.py` | — | — |
| `src/opencode_arch/cli/gap_analyzer.py` | — | — |
| `src/opencode_arch/cli/generate.py` | — | — |
| `src/opencode_arch/cli/launch.py` | — | — |
| `src/opencode_arch/cli/main.py` | — | — |
| `src/opencode_arch/cli/metrics.py` | — | — |
| `src/opencode_arch/cli/regen_loop.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| COMP-1 (Extraction Tools) | uses | CLI Commands imports from Extraction Tools |
| COMP-12 (Runner) | uses | CLI Commands imports from Runner |
| COMP-13 (Telemetry) | uses | CLI Commands imports from Telemetry |
| COMP-14 (Learning) | uses | CLI Commands imports from Learning |
| COMP-6 (Context Tools) | uses | CLI Commands imports from Context Tools |
| COMP-8 (Documentation Tools) | uses | CLI Commands imports from Documentation Tools |
| COMP-9 (Quality Gate Tools) | uses | CLI Commands imports from Quality Gate Tools |
| REQ-E1 | satisfies | — |
| REQ-I1 | satisfies | — |
| REQ-O1 | satisfies | — |
| REQ-Q1 | satisfies | — |
| REQ-Q10 | satisfies | — |
| REQ-Q11 | satisfies | — |
| REQ-Q2 | satisfies | — |
| REQ-Q3 | satisfies | — |
| REQ-Q4 | satisfies | — |
| REQ-Q5 | satisfies | — |
| REQ-Q6 | satisfies | — |
| REQ-Q7 | satisfies | — |
| REQ-Q8 | satisfies | — |
| REQ-Q9 | satisfies | — |
| IF-3 | exposes | — |
| REQ-Q16 | satisfies | — |
| REQ-Q17 | satisfies | — |

### Dependents (incoming)

None

## Behaviors Realized

None

## Interface Dependencies

- **requires** `uses_Tools` → COMP-1 (Extraction Tools) [store_extraction]
- **provides** `exposes_to_Tools` → COMP-1 (Extraction Tools) [drain_and_store]

## Patterns

None

## Confidence

55%
