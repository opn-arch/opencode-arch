---
document: Maintenance Manual
system: System
system_id: SYS-unknown
generated_at: 2026-08-18T20:07:47Z
generator_version: 0.3.0
model_hash: ceee27c08922
edition: 5
---

> **Model Completeness: F (0%)**
> Some sections may be empty due to missing model entities.
> - 56/56 components have no behavioral specification
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Maintenance Manual: System

## Component Inventory

| Component | Kind | Layer | Files | Signatures | Test Contracts |
|-----------|------|-------|-------|-----------|----------------|
| Quality (src-mcp-COMP-1) | service | — | 1 | 0 | 0 |
| Assess (src-mcp-COMP-2) | service | — | 1 | 0 | 0 |
| Author (src-mcp-COMP-3) | service | — | 1 | 0 | 0 |
| Check (src-mcp-COMP-4) | service | — | 1 | 0 | 0 |
| Correct (src-mcp-COMP-5) | service | — | 1 | 0 | 0 |
| Decompose (src-mcp-COMP-6) | service | — | 1 | 0 | 0 |
| Diff (src-mcp-COMP-7) | service | — | 1 | 0 | 0 |
| Docs (src-mcp-COMP-8) | service | — | 1 | 0 | 0 |
| Evaluate (src-mcp-COMP-9) | service | — | 1 | 0 | 0 |
| Export (src-mcp-COMP-10) | service | — | 1 | 0 | 0 |
| Extract (src-mcp-COMP-11) | service | — | 1 | 0 | 0 |
| Feedback (src-mcp-COMP-12) | service | — | 1 | 0 | 0 |
| Gate (src-mcp-COMP-13) | service | — | 1 | 0 | 0 |
| Generate (src-mcp-COMP-14) | service | — | 1 | 0 | 0 |
| Group (src-mcp-COMP-15) | service | — | 1 | 0 | 0 |
| Ingest (src-mcp-COMP-16) | service | — | 1 | 0 | 0 |
| Learn (src-mcp-COMP-17) | service | — | 1 | 0 | 0 |
| Llm Audit (src-mcp-COMP-18) | service | — | 1 | 0 | 0 |
| Log (src-mcp-COMP-19) | service | — | 1 | 0 | 0 |
| Pipeline (src-mcp-COMP-20) | service | — | 1 | 0 | 0 |
| Regen Score (src-mcp-COMP-21) | service | — | 1 | 0 | 0 |
| Require (src-mcp-COMP-22) | service | — | 1 | 0 | 0 |
| Scan (src-mcp-COMP-23) | service | — | 1 | 0 | 0 |
| Slice (src-mcp-COMP-24) | service | — | 1 | 0 | 0 |
| Stats (src-mcp-COMP-25) | service | — | 1 | 0 | 0 |
| Sync (src-mcp-COMP-26) | service | — | 1 | 0 | 0 |
| Trace Requirements (src-mcp-COMP-27) | service | — | 1 | 0 | 0 |
| Validate (src-mcp-COMP-28) | service | — | 1 | 0 | 0 |
| Infrastructure (src-mcp-COMP-29) | service | — | 2 | 0 | 0 |
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
| Benchmark Execution Scripts (COMP-2) | service | infra | 2 | 0 | 0 |
| Src (artifacts) (COMP-3-1) | service | data | 5 | 0 | 0 |
| LLM Prompt Relay (COMP-3-2) | service | data | 5 | 0 | 0 |
| Src (context) (COMP-3-3) | service | data | 3 | 0 | 0 |
| Src (learning) (COMP-3-4) | service | data | 7 | 0 | 0 |
| Src (runner) (COMP-3-5) | service | data | 2 | 0 | 0 |
| Src (agent) (COMP-3-6) | service | data | 1 | 0 | 0 |
| MCP Quality Server (COMP-3-7) | service | data | 30 | 0 | 0 |
| Src (requirements) (COMP-3-8) | service | data | 4 | 0 | 0 |
| CLI Commands (COMP-3-9) | service | data | 13 | 0 | 0 |
| Src (prompts) (COMP-3-10) | service | data | 1 | 0 | 0 |
| Src (extract) (COMP-3-11) | service | data | 1 | 0 | 0 |
| Src (telemetry) (COMP-3-12) | service | data | 3 | 0 | 0 |
| Src (regen) (COMP-3-13) | service | data | 2 | 0 | 0 |

## Dependency Impact Analysis

| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Quality | Scan, Stats, Evaluate, Require, Validate, Generate, Check, Sync, Regen Score, Assess, Ingest, Pipeline, Group, Correct, Slice, Export, Gate, Log, Decompose, Extract, Trace Requirements, Learn, Diff, Docs, Llm Audit, Author, Feedback | Trace Requirements, Infrastructure, Extract, Scan, Docs, Generate, Decompose, Pipeline, Export, Group, Check, Ingest, Llm Audit | HIGH |
| Assess | — | Quality, Slice | MEDIUM |
| Author | — | Slice, Quality | MEDIUM |
| Check | Infrastructure, Quality | Quality, Slice | MEDIUM |
| Correct | — | Quality, Slice | MEDIUM |
| Decompose | Infrastructure, Quality | Slice, Quality | MEDIUM |
| Diff | — | Sync, Slice, Quality | MEDIUM |
| Docs | Infrastructure, Quality | Slice, Quality | MEDIUM |
| Evaluate | — | Quality, Slice | MEDIUM |
| Export | Infrastructure, Quality | Quality, Slice | MEDIUM |
| Extract | Infrastructure, Quality | Slice, Trace Requirements, Quality | MEDIUM |
| Feedback | — | Slice, Quality | MEDIUM |
| Gate | — | Slice, Quality | MEDIUM |
| Generate | Infrastructure, Quality | Quality, Slice | MEDIUM |
| Group | Infrastructure, Quality | Quality, Slice | MEDIUM |
| Ingest | Infrastructure, Quality | Quality, Slice | MEDIUM |
| Learn | — | Slice, Quality | MEDIUM |
| Llm Audit | Infrastructure, Quality | Slice, Quality | MEDIUM |
| Log | — | Slice, Quality | MEDIUM |
| Pipeline | Infrastructure, Quality | Quality, Slice | MEDIUM |
| Regen Score | — | Quality, Slice | MEDIUM |
| Require | — | Trace Requirements, Quality, Slice | MEDIUM |
| Scan | Infrastructure, Quality | Quality, Slice | MEDIUM |
| Slice | Gate, Log, Decompose, Extract, Trace Requirements, Learn, Diff, Docs, Llm Audit, Author, Feedback, Scan, Stats, Evaluate, Require, Validate, Generate, Check, Sync, Regen Score, Assess, Ingest, Pipeline, Group, Correct, Export | Quality | LOW |
| Stats | — | Quality, Slice | MEDIUM |
| Sync | Diff | Quality, Slice | MEDIUM |
| Trace Requirements | Infrastructure, Require, Quality, Extract | Slice, Quality | MEDIUM |
| Validate | — | Quality, Slice | MEDIUM |
| Infrastructure | Quality | Trace Requirements, Generate, Extract, Scan, Docs, Decompose, Pipeline, Export, Group, Check, Ingest, Llm Audit | HIGH |
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
| Benchmark Execution Scripts | — | — | LOW |
| Src (artifacts) | — | — | LOW |
| LLM Prompt Relay | — | — | LOW |
| Src (context) | — | — | LOW |
| Src (learning) | — | — | LOW |
| Src (runner) | — | — | LOW |
| Src (agent) | — | — | LOW |
| MCP Quality Server | — | — | LOW |
| Src (requirements) | — | — | LOW |
| CLI Commands | — | — | LOW |
| Src (prompts) | — | — | LOW |
| Src (extract) | — | — | LOW |
| Src (telemetry) | — | — | LOW |
| Src (regen) | — | — | LOW |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Quality (src-mcp-COMP-1)

**Files:**
- `src/opencode_arch/mcp/quality.py`
**Downstream dependents (must re-test):** Trace Requirements, Infrastructure, Extract, Scan, Docs, Generate, Decompose, Pipeline, Export, Group, Check, Ingest, Llm Audit

### Assess (src-mcp-COMP-2)

**Files:**
- `src/opencode_arch/mcp/tools/assess.py`
**Downstream dependents (must re-test):** Quality, Slice

### Author (src-mcp-COMP-3)

**Files:**
- `src/opencode_arch/mcp/tools/author.py`
**Downstream dependents (must re-test):** Slice, Quality

### Check (src-mcp-COMP-4)

**Files:**
- `src/opencode_arch/mcp/tools/check.py`
**Downstream dependents (must re-test):** Quality, Slice

### Correct (src-mcp-COMP-5)

**Files:**
- `src/opencode_arch/mcp/tools/correct.py`
**Downstream dependents (must re-test):** Quality, Slice

### Decompose (src-mcp-COMP-6)

**Files:**
- `src/opencode_arch/mcp/tools/decompose.py`
**Downstream dependents (must re-test):** Slice, Quality

### Diff (src-mcp-COMP-7)

**Files:**
- `src/opencode_arch/mcp/tools/diff.py`
**Downstream dependents (must re-test):** Sync, Slice, Quality

### Docs (src-mcp-COMP-8)

**Files:**
- `src/opencode_arch/mcp/tools/docs.py`
**Downstream dependents (must re-test):** Slice, Quality

### Evaluate (src-mcp-COMP-9)

**Files:**
- `src/opencode_arch/mcp/tools/evaluate.py`
**Downstream dependents (must re-test):** Quality, Slice

### Export (src-mcp-COMP-10)

**Files:**
- `src/opencode_arch/mcp/tools/export.py`
**Downstream dependents (must re-test):** Quality, Slice

### Extract (src-mcp-COMP-11)

**Files:**
- `src/opencode_arch/mcp/tools/extract.py`
**Downstream dependents (must re-test):** Slice, Trace Requirements, Quality

### Feedback (src-mcp-COMP-12)

**Files:**
- `src/opencode_arch/mcp/tools/feedback.py`
**Downstream dependents (must re-test):** Slice, Quality

### Gate (src-mcp-COMP-13)

**Files:**
- `src/opencode_arch/mcp/tools/gate.py`
**Downstream dependents (must re-test):** Slice, Quality

### Generate (src-mcp-COMP-14)

**Files:**
- `src/opencode_arch/mcp/tools/generate.py`
**Downstream dependents (must re-test):** Quality, Slice

### Group (src-mcp-COMP-15)

**Files:**
- `src/opencode_arch/mcp/tools/group.py`
**Downstream dependents (must re-test):** Quality, Slice

### Ingest (src-mcp-COMP-16)

**Files:**
- `src/opencode_arch/mcp/tools/ingest.py`
**Downstream dependents (must re-test):** Quality, Slice

### Learn (src-mcp-COMP-17)

**Files:**
- `src/opencode_arch/mcp/tools/learn.py`
**Downstream dependents (must re-test):** Slice, Quality

### Llm Audit (src-mcp-COMP-18)

**Files:**
- `src/opencode_arch/mcp/tools/llm_audit.py`
**Downstream dependents (must re-test):** Slice, Quality

### Log (src-mcp-COMP-19)

**Files:**
- `src/opencode_arch/mcp/tools/log.py`
**Downstream dependents (must re-test):** Slice, Quality

### Pipeline (src-mcp-COMP-20)

**Files:**
- `src/opencode_arch/mcp/tools/pipeline.py`
**Downstream dependents (must re-test):** Quality, Slice

### Regen Score (src-mcp-COMP-21)

**Files:**
- `src/opencode_arch/mcp/tools/regen_score.py`
**Downstream dependents (must re-test):** Quality, Slice

### Require (src-mcp-COMP-22)

**Files:**
- `src/opencode_arch/mcp/tools/require.py`
**Downstream dependents (must re-test):** Trace Requirements, Quality, Slice

### Scan (src-mcp-COMP-23)

**Files:**
- `src/opencode_arch/mcp/tools/scan.py`
**Downstream dependents (must re-test):** Quality, Slice

### Slice (src-mcp-COMP-24)

**Files:**
- `src/opencode_arch/mcp/tools/slice.py`
**Downstream dependents (must re-test):** Quality

### Stats (src-mcp-COMP-25)

**Files:**
- `src/opencode_arch/mcp/tools/stats.py`
**Downstream dependents (must re-test):** Quality, Slice

### Sync (src-mcp-COMP-26)

**Files:**
- `src/opencode_arch/mcp/tools/sync.py`
**Downstream dependents (must re-test):** Quality, Slice

### Trace Requirements (src-mcp-COMP-27)

**Files:**
- `src/opencode_arch/mcp/tools/trace_requirements.py`
**Downstream dependents (must re-test):** Slice, Quality

### Validate (src-mcp-COMP-28)

**Files:**
- `src/opencode_arch/mcp/tools/validate.py`
**Downstream dependents (must re-test):** Quality, Slice

### Infrastructure (src-mcp-COMP-29)

**Files:**
- `src/opencode_arch/mcp/__main__.py`
- `src/opencode_arch/mcp/server.py`
**Downstream dependents (must re-test):** Trace Requirements, Generate, Extract, Scan, Docs, Decompose, Pipeline, Export, Group, Check, Ingest, Llm Audit

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

### Benchmark Execution Scripts (COMP-2)

**Files:**
- `scripts/benchmark_economy.py`
- `scripts/run_benchmark.py`

### Src (artifacts) (COMP-3-1)

**Files:**
- `src/opencode_arch/artifacts/__init__.py`
- `src/opencode_arch/artifacts/context.py`
- `src/opencode_arch/artifacts/diagrams.py`
- `src/opencode_arch/artifacts/selector.py`
- `src/opencode_arch/artifacts/templates.py`

### LLM Prompt Relay (COMP-3-2)

**Files:**
- `src/opencode_arch/llm/cache.py`
- `src/opencode_arch/llm/prompts/audit.py`
- `src/opencode_arch/llm/prompts/matching.py`
- `src/opencode_arch/llm/prompts/requirements.py`
- `src/opencode_arch/llm/relay.py`

### Src (context) (COMP-3-3)

**Files:**
- `src/opencode_arch/context/__init__.py`
- `src/opencode_arch/context/formatter.py`
- `src/opencode_arch/context/pipeline_bridge.py`

### Src (learning) (COMP-3-4)

**Files:**
- `src/opencode_arch/learning/__init__.py`
- `src/opencode_arch/learning/adapter.py`
- `src/opencode_arch/learning/assessor.py`
- `src/opencode_arch/learning/classifier.py`
- `src/opencode_arch/learning/lessons.py`
- `src/opencode_arch/learning/maintainer.py`
- `src/opencode_arch/learning/patterns.py`

### Src (runner) (COMP-3-5)

**Files:**
- `src/opencode_arch/runner/base.py`
- `src/opencode_arch/runner/opencode.py`

### Src (agent) (COMP-3-6)

**Files:**
- `src/opencode_arch/agent/resolution.py`

### MCP Quality Server (COMP-3-7)

**Files:**
- `src/opencode_arch/mcp/__main__.py`
- `src/opencode_arch/mcp/quality.py`
- `src/opencode_arch/mcp/server.py`
- `src/opencode_arch/mcp/tools/assess.py`
- `src/opencode_arch/mcp/tools/author.py`
- `src/opencode_arch/mcp/tools/check.py`
- `src/opencode_arch/mcp/tools/correct.py`
- `src/opencode_arch/mcp/tools/decompose.py`
- `src/opencode_arch/mcp/tools/diff.py`
- `src/opencode_arch/mcp/tools/docs.py`
- `src/opencode_arch/mcp/tools/evaluate.py`
- `src/opencode_arch/mcp/tools/export.py`
- `src/opencode_arch/mcp/tools/extract.py`
- `src/opencode_arch/mcp/tools/feedback.py`
- `src/opencode_arch/mcp/tools/gate.py`
- `src/opencode_arch/mcp/tools/generate.py`
- `src/opencode_arch/mcp/tools/group.py`
- `src/opencode_arch/mcp/tools/ingest.py`
- `src/opencode_arch/mcp/tools/learn.py`
- `src/opencode_arch/mcp/tools/llm_audit.py`
- *...and 10 more files*

### Src (requirements) (COMP-3-8)

**Files:**
- `src/opencode_arch/requirements/llm_extractor.py`
- `src/opencode_arch/requirements/matcher.py`
- `src/opencode_arch/requirements/parser.py`
- `src/opencode_arch/requirements/retroactive.py`

### CLI Commands (COMP-3-9)

**Files:**
- `src/opencode_arch/cli/bench.py`
- `src/opencode_arch/cli/calibrate.py`
- `src/opencode_arch/cli/confidence.py`
- `src/opencode_arch/cli/docs.py`
- `src/opencode_arch/cli/docs_validator.py`
- `src/opencode_arch/cli/extract.py`
- `src/opencode_arch/cli/gap_analyzer.py`
- `src/opencode_arch/cli/generate.py`
- `src/opencode_arch/cli/launch.py`
- `src/opencode_arch/cli/main.py`
- `src/opencode_arch/cli/metrics.py`
- `src/opencode_arch/cli/prompts.py`
- `src/opencode_arch/cli/regen_loop.py`

### Src (prompts) (COMP-3-10)

**Files:**
- `src/opencode_arch/prompts/regen.py`

### Src (extract) (COMP-3-11)

**Files:**
- `src/opencode_arch/extract/__init__.py`

### Src (telemetry) (COMP-3-12)

**Files:**
- `src/opencode_arch/telemetry/collector.py`
- `src/opencode_arch/telemetry/recorder.py`
- `src/opencode_arch/telemetry/store.py`

### Src (regen) (COMP-3-13)

**Files:**
- `src/opencode_arch/regen/self_heal.py`
- `src/opencode_arch/regen/spot_check.py`

## Known Constraints

*No constraint allocations defined.*
