---
document: Maintenance Manual
system: Src (cli)
system_id: SYS-unknown
generated_at: 2026-08-18T12:58:40Z
generator_version: 0.3.0
model_hash: 4a18118f967e
edition: 13
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
| Bench | Docs Validator, Launch, Main, Generate, Gap Analyzer, Regen Loop, Metrics, Confidence, Infrastructure, Extract, Docs | Extract, Regen Loop, Generate | MEDIUM |
| Calibrate | — | — | LOW |
| Confidence | — | Regen Loop, Generate, Bench, Extract | MEDIUM |
| Docs | — | Extract, Regen Loop, Generate, Bench | MEDIUM |
| Docs Validator | — | Bench, Extract, Regen Loop, Generate | MEDIUM |
| Extract | Docs, Docs Validator, Bench, Launch, Main, Generate, Gap Analyzer, Metrics, Regen Loop, Confidence, Infrastructure | Regen Loop, Generate, Bench | MEDIUM |
| Gap Analyzer | — | Generate, Bench, Extract, Regen Loop | MEDIUM |
| Generate | Main, Gap Analyzer, Metrics, Regen Loop, Confidence, Infrastructure, Extract, Docs, Docs Validator, Bench, Launch | Bench, Extract, Regen Loop | MEDIUM |
| Launch | — | Bench, Extract, Regen Loop, Generate | MEDIUM |
| Main | — | Generate, Bench, Extract, Regen Loop | MEDIUM |
| Metrics | — | Regen Loop, Generate, Bench, Extract | MEDIUM |
| Regen Loop | Confidence, Metrics, Infrastructure, Docs, Extract, Docs Validator, Bench, Launch, Main, Generate, Gap Analyzer | Generate, Bench, Extract | MEDIUM |
| Infrastructure | — | Regen Loop, Generate, Bench, Extract | MEDIUM |

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
**Downstream dependents (must re-test):** Regen Loop, Generate, Bench, Extract

### Docs (src-cli-COMP-4)

**Files:**
- `src/opencode_arch/cli/docs.py`
**Downstream dependents (must re-test):** Extract, Regen Loop, Generate, Bench

### Docs Validator (src-cli-COMP-5)

**Files:**
- `src/opencode_arch/cli/docs_validator.py`
**Downstream dependents (must re-test):** Bench, Extract, Regen Loop, Generate

### Extract (src-cli-COMP-6)

**Files:**
- `src/opencode_arch/cli/extract.py`
**Downstream dependents (must re-test):** Regen Loop, Generate, Bench

### Gap Analyzer (src-cli-COMP-7)

**Files:**
- `src/opencode_arch/cli/gap_analyzer.py`
**Downstream dependents (must re-test):** Generate, Bench, Extract, Regen Loop

### Generate (src-cli-COMP-8)

**Files:**
- `src/opencode_arch/cli/generate.py`
**Downstream dependents (must re-test):** Bench, Extract, Regen Loop

### Launch (src-cli-COMP-9)

**Files:**
- `src/opencode_arch/cli/launch.py`
**Downstream dependents (must re-test):** Bench, Extract, Regen Loop, Generate

### Main (src-cli-COMP-10)

**Files:**
- `src/opencode_arch/cli/main.py`
**Downstream dependents (must re-test):** Generate, Bench, Extract, Regen Loop

### Metrics (src-cli-COMP-11)

**Files:**
- `src/opencode_arch/cli/metrics.py`
**Downstream dependents (must re-test):** Regen Loop, Generate, Bench, Extract

### Regen Loop (src-cli-COMP-12)

**Files:**
- `src/opencode_arch/cli/regen_loop.py`
**Downstream dependents (must re-test):** Generate, Bench, Extract

### Infrastructure (src-cli-COMP-13)

**Files:**
- `src/opencode_arch/cli/prompts.py`
**Downstream dependents (must re-test):** Regen Loop, Generate, Bench, Extract

## Known Constraints

*No constraint allocations defined.*
