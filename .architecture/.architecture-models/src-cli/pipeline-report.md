# Pipeline Report: Src (cli)

**Generated:** 2026-08-18T12:22:25Z
**Total Duration:** 209ms
**Stages:** 7

## LLM Summary

No LLM calls — deterministic pipeline run

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 100 | 209ms | 0 |
| infer | 92 | 0ms | 0 |
| allocate | 50 | 0ms | 0 |
| contract | 0 | 0ms | 0 |
| relate | 100 | 0ms | 0 |
| specify | 50 | 0ms | 0 |
| validate | 90 | 0ms | 0 |

## Stage: observe
**Score:** 100 | **Duration:** 209ms

### Deterministic Findings
- Discovered 13 modules
- 59 functions, 5 classes
- 4 import edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: infer
**Score:** 92 | **Duration:** 0ms

### Deterministic Findings
- Inferred 13 capabilities
- 1 actors
- 1 behaviors

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- ambiguous_module: src/opencode_arch/cli/prompts.py has no clear capability affiliation

## Stage: allocate
**Score:** 50 | **Duration:** 0ms

### Deterministic Findings
- 13 components
- File coverage: 10000%
- 0 unallocated files

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: contract
**Score:** 0 | **Duration:** 0ms

### Deterministic Findings
- 0 contracts

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: relate
**Score:** 100 | **Duration:** 0ms

### Deterministic Findings
- 44 depends-on relationships
- 13 contains relationships
- 12 realizes relationships
- 4 uses relationships

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: specify
**Score:** 50 | **Duration:** 0ms

### Deterministic Findings
- 1 interfaces

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: validate
**Score:** 90 | **Duration:** 0ms

### Deterministic Findings
- Score: 90/100
- 3 issues

### LLM Calls
*(none)*

### Diagnostics
*(none)*
