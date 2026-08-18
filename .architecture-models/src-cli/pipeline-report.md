# Pipeline Report: Src (cli)

**Generated:** 2026-08-18T23:31:28Z
**Total Duration:** 246ms
**Stages:** 7

## LLM Summary

No LLM calls — deterministic pipeline run

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 100 | 245ms | 0 |
| infer | 92 | 0ms | 0 |
| allocate | 50 | 0ms | 0 |
| contract | 0 | 0ms | 0 |
| relate | 100 | 1ms | 0 |
| specify | 50 | 0ms | 0 |
| validate | 90 | 0ms | 0 |

## Stage: observe
**Score:** 100 | **Duration:** 245ms

### Deterministic Findings
- Discovered 14 modules
- 60 functions, 5 classes
- 4 import edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: infer
**Score:** 92 | **Duration:** 0ms

### Deterministic Findings
- Inferred 14 capabilities
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
- 14 components
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
**Score:** 100 | **Duration:** 1ms

### Deterministic Findings
- 48 depends-on relationships
- 14 contains relationships
- 13 realizes relationships
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
