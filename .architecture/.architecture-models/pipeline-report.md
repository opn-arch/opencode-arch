# Pipeline Report: System-of-Systems

**Generated:** 2026-08-19T16:58:19Z
**Total Duration:** 569ms
**Stages:** 8

## LLM Summary

No LLM calls — deterministic pipeline run

## Stage Scores

| Stage | Score | Duration | LLM Calls |
|-------|-------|----------|-----------|
| observe | 100 | 503ms | 0 |
| infer | 58 | 1ms | 0 |
| allocate | 83 | 0ms | 0 |
| contract | 71 | 0ms | 0 |
| relate | 100 | 65ms | 0 |
| specify | 85 | 0ms | 0 |
| decompose | 100.0 | 0ms | 0 |
| validate | 80 | 0ms | 0 |

## Stage: observe
**Score:** 100 | **Duration:** 503ms

### Deterministic Findings
- Discovered 165 modules
- 373 functions, 152 classes
- 147 import edges

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: infer
**Score:** 58 | **Duration:** 1ms

### Deterministic Findings
- Inferred 6 capabilities
- 1 actors
- 3 behaviors

### LLM Calls
*(none)*

### Diagnostics
*(none)*

### Uncertainties
- complex_behavior: TelemetryStore in src/opencode_arch/telemetry/store.py has 18 public methods — needs LLM analysis to identify key workflows and use cases
- ambiguous_module: src/opencode_arch/artifacts/selector.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/artifacts/templates.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/artifacts/context.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/artifacts/diagrams.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/llm/cache.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/llm/relay.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/context/formatter.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/context/pipeline_bridge.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/learning/assessor.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/learning/classifier.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/learning/lessons.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/learning/patterns.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/learning/adapter.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/learning/maintainer.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/agent/resolution.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/server.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/quality.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/__main__.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/requirements/matcher.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/requirements/parser.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/requirements/llm_extractor.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/requirements/retroactive.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/metrics.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/regen_loop.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/export_data.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/confidence.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/generate.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/docs.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/prompts.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/gap_analyzer.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/launch.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/docs_validator.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/calibrate.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/cli/extract.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/prompts/regen.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/telemetry/store.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/telemetry/recorder.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/telemetry/collector.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/regen/spot_check.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/regen/self_heal.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/sync.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/ingest.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/llm_audit.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/check.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/correct.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/slice.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/decompose.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/log.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/generate.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/feedback.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/trace_requirements.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/regen_score.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/author.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/docs.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/export.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/assess.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/validate.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/pipeline.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/stats.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/gate.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/learn.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/scan.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/diff.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/evaluate.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/require.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/mcp/tools/extract.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/llm/prompts/audit.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/llm/prompts/matching.py has no clear capability affiliation
- ambiguous_module: src/opencode_arch/llm/prompts/requirements.py has no clear capability affiliation

## Stage: allocate
**Score:** 83 | **Duration:** 0ms

### Deterministic Findings
- 14 components
- File coverage: 10000%
- 0 unallocated files

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: contract
**Score:** 71 | **Duration:** 0ms

### Deterministic Findings
- 61 contracts

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: relate
**Score:** 100 | **Duration:** 65ms

### Deterministic Findings
- 39 depends-on relationships
- 14 realizes relationships
- 14 contains relationships

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: specify
**Score:** 85 | **Duration:** 0ms

### Deterministic Findings
- 13 interfaces

### LLM Calls
*(none)*

### Diagnostics
*(none)*

## Stage: decompose
**Score:** 100.0 | **Duration:** 0ms

### Deterministic Findings
- 5 systems
- 9 inline components
- 39 inter-system edges

### LLM Calls
*(none)*

### Diagnostics
- ℹ️ HIERARCHY_CREATED: Created 2 sub-components across 1 components

## Stage: validate
**Score:** 80 | **Duration:** 0ms

### Deterministic Findings
- Score: 80/100
- 4 issues

### LLM Calls
*(none)*

### Diagnostics
*(none)*
