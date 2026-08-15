# Pipeline Report: opencode-arch

**Generated:** 2026-08-11T17:18:41Z
**Total Duration:** 698ms
**Stages:** 10

## LLM Summary

No LLM calls — deterministic pipeline run

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 99 | 484ms | 0 |
| infer | 83 | 0ms | 0 |
| allocate | 100 | 3ms | 0 |
| contract | 72 | 0ms | 0 |
| relate | 81 | 31ms | 0 |
| specify | 50 | 0ms | 0 |
| decompose | 100.0 | 0ms | 0 |
| validate | 100 | 0ms | 0 |
| synthesize | 100.0 | 179ms | 0 |
| emit | 100.0 | 1ms | 0 |

## Stage: observe
**Score:** 99 | **Duration:** 484ms

### Deterministic Findings
- Discovered 155 modules
- 341 functions, 148 classes
- 0 import edges

### LLM Calls
*(none)*

### Diagnostics
- ⚠️ parse-failed: Parse failed: src/opencode_arch/cli/export_data.py: unindent does not match any outer indentation level (export_data.py, line 74)

## Stage: infer
**Score:** 83 | **Duration:** 0ms

### Deterministic Findings
- Inferred 14 capabilities
- 1 actors
- 0 behaviors

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- ambiguous_module: src/opencode_arch/learning/assessor.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/learning/classifier.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/learning/lessons.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/learning/adapter.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/learning/maintainer.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/server.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/__main__.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/requirements/matcher.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/requirements/parser.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/requirements/llm_extractor.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/requirements/retroactive.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/regen_loop.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/confidence.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/generate.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/prompts.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/bench.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/gap_analyzer.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/launch.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/extract.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/telemetry/store.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/telemetry/recorder.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/telemetry/collector.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/regen/self_heal.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/llm/prompts/audit.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/llm/prompts/matching.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/llm/prompts/requirements.py has no clear capability affiliation

## Stage: allocate
**Score:** 100 | **Duration:** 3ms

### Deterministic Findings
- 22 components
- File coverage: 10000%
- 0 unallocated files

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: contract
**Score:** 72 | **Duration:** 0ms

### Deterministic Findings
- 43 contracts

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: relate
**Score:** 81 | **Duration:** 31ms

### Deterministic Findings
- 36 depends-on relationships
- 22 contains relationships
- 14 realizes relationships

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

## Stage: decompose
**Score:** 100.0 | **Duration:** 0ms

### Deterministic Findings
- 1 systems
- 21 inline components
- 36 inter-system edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: validate
**Score:** 100 | **Duration:** 0ms

### Deterministic Findings
- Score: 100/100
- 0 issues

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: synthesize
**Score:** 100.0 | **Duration:** 179ms

### Deterministic Findings
*(none)*

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: emit
**Score:** 100.0 | **Duration:** 1ms

### Deterministic Findings
*(none)*

### LLM Calls
*(none)*

### Diagnostics
*(none)*
