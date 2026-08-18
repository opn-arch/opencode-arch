---
document: Maintenance Manual
system: Src (cli)
system_id: SYS-unknown
generated_at: 2026-08-18T20:07:49Z
generator_version: 0.3.0
model_hash: 4a18118f967e
edition: 3
---

> **Model Completeness: F (2%)**
> Some sections may be empty due to missing model entities.
> - 13/13 components have no behavioral specification
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Maintenance Manual: Src (cli)

## Component Inventory

| Component | Kind | Layer | Files | Signatures | Test Contracts |
|-----------|------|-------|-------|-----------|----------------|
| Bench (src-cli-COMP-1) | service | — | 1 | 0 | 0 |
| Calibrate (src-cli-COMP-2) | service | — | 1 | 0 | 0 |
| Confidence (src-cli-COMP-3) | service | — | 1 | 0 | 0 |
| Docs (src-cli-COMP-4) | service | — | 1 | 0 | 0 |
| Docs Validator (src-cli-COMP-5) | service | — | 1 | 0 | 0 |
| Extract (src-cli-COMP-6) | service | — | 1 | 0 | 0 |
| Gap Analyzer (src-cli-COMP-7) | service | — | 1 | 0 | 0 |
| Generate (src-cli-COMP-8) | service | — | 1 | 0 | 0 |
| Launch (src-cli-COMP-9) | service | — | 1 | 0 | 0 |
| Main (src-cli-COMP-10) | service | — | 1 | 0 | 0 |
| Metrics (src-cli-COMP-11) | service | — | 1 | 0 | 0 |
| Regen Loop (src-cli-COMP-12) | service | — | 1 | 0 | 0 |
| Infrastructure (src-cli-COMP-13) | service | — | 1 | 0 | 0 |

## Dependency Impact Analysis

| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Bench | Launch, Metrics, Main, Infrastructure, Gap Analyzer, Generate, Confidence, Extract, Docs, Regen Loop, Docs Validator | Extract, Regen Loop, Generate | MEDIUM |
| Calibrate | — | — | LOW |
| Confidence | — | Generate, Extract, Bench, Regen Loop | MEDIUM |
| Docs | — | Regen Loop, Generate, Extract, Bench | MEDIUM |
| Docs Validator | — | Regen Loop, Generate, Extract, Bench | MEDIUM |
| Extract | Launch, Metrics, Bench, Main, Infrastructure, Generate, Confidence, Gap Analyzer, Regen Loop, Docs Validator, Docs | Regen Loop, Generate, Bench | MEDIUM |
| Gap Analyzer | — | Generate, Extract, Bench, Regen Loop | MEDIUM |
| Generate | Infrastructure, Gap Analyzer, Confidence, Extract, Regen Loop, Docs Validator, Docs, Launch, Metrics, Main, Bench | Extract, Regen Loop, Bench | MEDIUM |
| Launch | — | Extract, Bench, Regen Loop, Generate | MEDIUM |
| Main | — | Extract, Bench, Regen Loop, Generate | MEDIUM |
| Metrics | — | Extract, Bench, Regen Loop, Generate | MEDIUM |
| Regen Loop | Extract, Docs Validator, Docs, Launch, Metrics, Bench, Main, Generate, Infrastructure, Confidence, Gap Analyzer | Generate, Extract, Bench | MEDIUM |
| Infrastructure | — | Generate, Extract, Bench, Regen Loop | MEDIUM |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Bench (src-cli-COMP-1)

**Files:**
- `src/opencode_arch/cli/bench.py`
**Downstream dependents (must re-test):** Extract, Regen Loop, Generate

### Calibrate (src-cli-COMP-2)

**Files:**
- `src/opencode_arch/cli/calibrate.py`

### Confidence (src-cli-COMP-3)

**Files:**
- `src/opencode_arch/cli/confidence.py`
**Downstream dependents (must re-test):** Generate, Extract, Bench, Regen Loop

### Docs (src-cli-COMP-4)

**Files:**
- `src/opencode_arch/cli/docs.py`
**Downstream dependents (must re-test):** Regen Loop, Generate, Extract, Bench

### Docs Validator (src-cli-COMP-5)

**Files:**
- `src/opencode_arch/cli/docs_validator.py`
**Downstream dependents (must re-test):** Regen Loop, Generate, Extract, Bench

### Extract (src-cli-COMP-6)

**Files:**
- `src/opencode_arch/cli/extract.py`
**Downstream dependents (must re-test):** Regen Loop, Generate, Bench

### Gap Analyzer (src-cli-COMP-7)

**Files:**
- `src/opencode_arch/cli/gap_analyzer.py`
**Downstream dependents (must re-test):** Generate, Extract, Bench, Regen Loop

### Generate (src-cli-COMP-8)

**Files:**
- `src/opencode_arch/cli/generate.py`
**Downstream dependents (must re-test):** Extract, Regen Loop, Bench

### Launch (src-cli-COMP-9)

**Files:**
- `src/opencode_arch/cli/launch.py`
**Downstream dependents (must re-test):** Extract, Bench, Regen Loop, Generate

### Main (src-cli-COMP-10)

**Files:**
- `src/opencode_arch/cli/main.py`
**Downstream dependents (must re-test):** Extract, Bench, Regen Loop, Generate

### Metrics (src-cli-COMP-11)

**Files:**
- `src/opencode_arch/cli/metrics.py`
**Downstream dependents (must re-test):** Extract, Bench, Regen Loop, Generate

### Regen Loop (src-cli-COMP-12)

**Files:**
- `src/opencode_arch/cli/regen_loop.py`
**Downstream dependents (must re-test):** Generate, Extract, Bench

### Infrastructure (src-cli-COMP-13)

**Files:**
- `src/opencode_arch/cli/prompts.py`
**Downstream dependents (must re-test):** Generate, Extract, Bench, Regen Loop

## Known Constraints

*No constraint allocations defined.*
