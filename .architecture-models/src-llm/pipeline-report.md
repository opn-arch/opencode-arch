# Pipeline Report: Src (llm)

**Generated:** 2026-08-18T20:07:46Z
**Total Duration:** 185ms
**Stages:** 2

## LLM Summary

No LLM calls — deterministic pipeline run

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 100 | 185ms | 0 |
| infer | 40 | 0ms | 0 |

## Stage: observe
**Score:** 100 | **Duration:** 185ms

### Deterministic Findings
- Discovered 5 modules
- 5 functions, 2 classes
- 0 import edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: infer
**Score:** 40 | **Duration:** 0ms

### Deterministic Findings
- Inferred 2 capabilities
- 1 actors
- 0 behaviors

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- ambiguous_module: src/opencode_arch/llm/prompts/audit.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/llm/prompts/matching.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/llm/prompts/requirements.py has no clear capability affiliation
