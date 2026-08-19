---
document: Maintenance Manual
system: Src (cli)
system_id: SYS-unknown
generated_at: 2026-08-19T16:59:44Z
generator_version: 0.3.0
model_hash: b65cb1b8e8a2
edition: 6
---

> **Model Completeness: F (1%)**
> Some sections may be empty due to missing model entities.
> - 14/14 components have no behavioral specification
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
| Export Data (src-cli-COMP-6) | service | — | 1 | 0 | 0 |
| Extract (src-cli-COMP-7) | service | — | 1 | 0 | 0 |
| Gap Analyzer (src-cli-COMP-8) | service | — | 1 | 0 | 0 |
| Generate (src-cli-COMP-9) | service | — | 1 | 0 | 0 |
| Launch (src-cli-COMP-10) | service | — | 1 | 0 | 0 |
| Main (src-cli-COMP-11) | service | — | 1 | 0 | 0 |
| Metrics (src-cli-COMP-12) | service | — | 1 | 0 | 0 |
| Regen Loop (src-cli-COMP-13) | service | — | 1 | 0 | 0 |
| Infrastructure (src-cli-COMP-14) | service | — | 1 | 0 | 0 |

## Dependency Impact Analysis

| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Bench | Infrastructure, Gap Analyzer, Confidence, Metrics, Docs Validator, Launch, Extract, Regen Loop, Export Data, Generate, Main, Docs | Regen Loop, Extract, Generate | MEDIUM |
| Calibrate | — | — | LOW |
| Confidence | — | Bench, Regen Loop, Extract, Generate | MEDIUM |
| Docs | — | Regen Loop, Extract, Generate, Bench | MEDIUM |
| Docs Validator | — | Extract, Generate, Bench, Regen Loop | MEDIUM |
| Export Data | — | Extract, Generate, Bench, Regen Loop | MEDIUM |
| Extract | Docs Validator, Regen Loop, Export Data, Generate, Main, Bench, Docs, Infrastructure, Gap Analyzer, Confidence, Metrics, Launch | Generate, Bench, Regen Loop | MEDIUM |
| Gap Analyzer | — | Bench, Regen Loop, Extract, Generate | MEDIUM |
| Generate | Metrics, Docs Validator, Launch, Extract, Regen Loop, Export Data, Bench, Main, Docs, Infrastructure, Gap Analyzer, Confidence | Extract, Bench, Regen Loop | MEDIUM |
| Launch | — | Generate, Bench, Regen Loop, Extract | MEDIUM |
| Main | — | Regen Loop, Extract, Generate, Bench | MEDIUM |
| Metrics | — | Generate, Bench, Regen Loop, Extract | MEDIUM |
| Regen Loop | Bench, Main, Docs, Infrastructure, Gap Analyzer, Confidence, Metrics, Docs Validator, Launch, Extract, Export Data, Generate | Extract, Generate, Bench | MEDIUM |
| Infrastructure | — | Bench, Regen Loop, Extract, Generate | MEDIUM |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Bench (src-cli-COMP-1)

**Files:**
- `src/opencode_arch/cli/bench.py`
**Downstream dependents (must re-test):** Regen Loop, Extract, Generate

### Calibrate (src-cli-COMP-2)

**Files:**
- `src/opencode_arch/cli/calibrate.py`

### Confidence (src-cli-COMP-3)

**Files:**
- `src/opencode_arch/cli/confidence.py`
**Downstream dependents (must re-test):** Bench, Regen Loop, Extract, Generate

### Docs (src-cli-COMP-4)

**Files:**
- `src/opencode_arch/cli/docs.py`
**Downstream dependents (must re-test):** Regen Loop, Extract, Generate, Bench

### Docs Validator (src-cli-COMP-5)

**Files:**
- `src/opencode_arch/cli/docs_validator.py`
**Downstream dependents (must re-test):** Extract, Generate, Bench, Regen Loop

### Export Data (src-cli-COMP-6)

**Files:**
- `src/opencode_arch/cli/export_data.py`
**Downstream dependents (must re-test):** Extract, Generate, Bench, Regen Loop

### Extract (src-cli-COMP-7)

**Files:**
- `src/opencode_arch/cli/extract.py`
**Downstream dependents (must re-test):** Generate, Bench, Regen Loop

### Gap Analyzer (src-cli-COMP-8)

**Files:**
- `src/opencode_arch/cli/gap_analyzer.py`
**Downstream dependents (must re-test):** Bench, Regen Loop, Extract, Generate

### Generate (src-cli-COMP-9)

**Files:**
- `src/opencode_arch/cli/generate.py`
**Downstream dependents (must re-test):** Extract, Bench, Regen Loop

### Launch (src-cli-COMP-10)

**Files:**
- `src/opencode_arch/cli/launch.py`
**Downstream dependents (must re-test):** Generate, Bench, Regen Loop, Extract

### Main (src-cli-COMP-11)

**Files:**
- `src/opencode_arch/cli/main.py`
**Downstream dependents (must re-test):** Regen Loop, Extract, Generate, Bench

### Metrics (src-cli-COMP-12)

**Files:**
- `src/opencode_arch/cli/metrics.py`
**Downstream dependents (must re-test):** Generate, Bench, Regen Loop, Extract

### Regen Loop (src-cli-COMP-13)

**Files:**
- `src/opencode_arch/cli/regen_loop.py`
**Downstream dependents (must re-test):** Extract, Generate, Bench

### Infrastructure (src-cli-COMP-14)

**Files:**
- `src/opencode_arch/cli/prompts.py`
**Downstream dependents (must re-test):** Bench, Regen Loop, Extract, Generate

## Known Constraints

*No constraint allocations defined.*
