# Pipeline Report: Src (mcp)

**Generated:** 2026-08-18T12:22:25Z
**Total Duration:** 247ms
**Stages:** 7

## LLM Summary

No LLM calls — deterministic pipeline run

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 100 | 243ms | 0 |
| infer | 93 | 0ms | 0 |
| allocate | 53 | 0ms | 0 |
| contract | 0 | 0ms | 0 |
| relate | 100 | 4ms | 0 |
| specify | 50 | 0ms | 0 |
| validate | 100 | 0ms | 0 |

## Stage: observe
**Score:** 100 | **Duration:** 243ms

### Deterministic Findings
- Discovered 30 modules
- 64 functions, 1 classes
- 13 import edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: infer
**Score:** 93 | **Duration:** 0ms

### Deterministic Findings
- Inferred 28 capabilities
- 1 actors
- 0 behaviors

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- ambiguous_module: src/opencode_arch/mcp/__main__.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/server.py has no clear capability affiliation

## Stage: allocate
**Score:** 53 | **Duration:** 0ms

### Deterministic Findings
- 29 components
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
**Score:** 100 | **Duration:** 4ms

### Deterministic Findings
- 81 depends-on relationships
- 29 contains relationships
- 28 realizes relationships

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: specify
**Score:** 50 | **Duration:** 0ms

### Deterministic Findings
- 0 interfaces

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: validate
**Score:** 100 | **Duration:** 0ms

### Deterministic Findings
- Score: 100/100
- 1 issues

### LLM Calls
*(none)*

### Diagnostics
*(none)*
