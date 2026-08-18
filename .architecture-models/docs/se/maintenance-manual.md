---
document: Maintenance Manual
system: System
system_id: SYS-unknown
generated_at: 2026-08-18T23:31:29Z
generator_version: 0.3.0
model_hash: efca59bc201d
edition: 7
---

> **Model Completeness: F (0%)**
> Some sections may be empty due to missing model entities.
> - 57/57 components have no behavioral specification
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
| Export Data (src-cli-COMP-6) | service | — | 1 | 0 | 0 |
| Extract (src-cli-COMP-7) | service | — | 1 | 0 | 0 |
| Gap Analyzer (src-cli-COMP-8) | service | — | 1 | 0 | 0 |
| Generate (src-cli-COMP-9) | service | — | 1 | 0 | 0 |
| Launch (src-cli-COMP-10) | service | — | 1 | 0 | 0 |
| Main (src-cli-COMP-11) | service | — | 1 | 0 | 0 |
| Metrics (src-cli-COMP-12) | service | — | 1 | 0 | 0 |
| Regen Loop (src-cli-COMP-13) | service | — | 1 | 0 | 0 |
| Infrastructure (src-cli-COMP-14) | service | — | 1 | 0 | 0 |
| Benchmark Scripts (COMP-2) | service | infra | 2 | 0 | 0 |
| Src (artifacts) (COMP-3-1) | service | data | 5 | 0 | 0 |
| LLM Integration Layer (COMP-3-2) | service | data | 5 | 0 | 0 |
| Src (context) (COMP-3-3) | service | data | 3 | 0 | 0 |
| Src (learning) (COMP-3-4) | service | data | 7 | 0 | 0 |
| Src (runner) (COMP-3-5) | service | data | 2 | 0 | 0 |
| Src (agent) (COMP-3-6) | service | data | 1 | 0 | 0 |
| MCP Quality Server (COMP-3-7) | service | data | 30 | 0 | 0 |
| Src (requirements) (COMP-3-8) | service | data | 4 | 0 | 0 |
| CLI Commands (COMP-3-9) | service | data | 14 | 0 | 0 |
| Src (prompts) (COMP-3-10) | service | data | 1 | 0 | 0 |
| Src (extract) (COMP-3-11) | service | data | 1 | 0 | 0 |
| Src (telemetry) (COMP-3-12) | service | data | 3 | 0 | 0 |
| Src (regen) (COMP-3-13) | service | data | 2 | 0 | 0 |
## Dependency Impact Analysis
| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |
|-----------|---------------------|---------------------|-------------|
| Quality | Llm Audit, Slice, Ingest, Validate, Regen Score, Check, Generate, Group, Feedback, Correct, Sync, Trace Requirements, Author, Scan, Assess, Stats, Diff, Decompose, Evaluate, Extract, Require, Docs, Pipeline, Learn, Export, Gate, Log | Export, Scan, Pipeline, Extract, Ingest, Group, Check, Generate, Llm Audit, Docs, Decompose, Infrastructure, Trace Requirements | HIGH |
| Assess | — | Slice, Quality | MEDIUM |
| Author | — | Slice, Quality | MEDIUM |
| Check | Infrastructure, Quality | Slice, Quality | MEDIUM |
| Correct | — | Slice, Quality | MEDIUM |
| Decompose | Infrastructure, Quality | Slice, Quality | MEDIUM |
| Diff | — | Slice, Quality, Sync | MEDIUM |
| Docs | Infrastructure, Quality | Slice, Quality | MEDIUM |
| Evaluate | — | Slice, Quality | MEDIUM |
| Export | Quality, Infrastructure | Slice, Quality | MEDIUM |
| Extract | Infrastructure, Quality | Trace Requirements, Slice, Quality | MEDIUM |
| Feedback | — | Slice, Quality | MEDIUM |
| Gate | — | Slice, Quality | MEDIUM |
| Generate | Infrastructure, Quality | Quality, Slice | MEDIUM |
| Group | Infrastructure, Quality | Slice, Quality | MEDIUM |
| Ingest | Infrastructure, Quality | Quality, Slice | MEDIUM |
| Learn | — | Slice, Quality | MEDIUM |
| Llm Audit | Infrastructure, Quality | Quality, Slice | MEDIUM |
| Log | — | Slice, Quality | MEDIUM |
| Pipeline | Quality, Infrastructure | Slice, Quality | MEDIUM |
| Regen Score | — | Quality, Slice | MEDIUM |
| Require | — | Trace Requirements, Slice, Quality | MEDIUM |
| Scan | Infrastructure, Quality | Slice, Quality | MEDIUM |
| Slice | Check, Author, Assess, Group, Feedback, Correct, Sync, Evaluate, Require, Docs, Trace Requirements, Scan, Learn, Export, Stats, Diff, Decompose, Extract, Llm Audit, Pipeline, Ingest, Validate, Gate, Regen Score, Log, Generate | Quality | LOW |
| Stats | — | Slice, Quality | MEDIUM |
| Sync | Diff | Slice, Quality | MEDIUM |
| Trace Requirements | Extract, Require, Infrastructure, Quality | Slice, Quality | MEDIUM |
| Validate | — | Quality, Slice | MEDIUM |
| Infrastructure | Quality | Ingest, Scan, Extract, Check, Generate, Group, Docs, Llm Audit, Decompose, Trace Requirements, Export, Pipeline | HIGH |
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
| Benchmark Scripts | — | — | LOW |
| Src (artifacts) | — | — | LOW |
| LLM Integration Layer | — | — | LOW |
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
**Downstream dependents (must re-test):** Export, Scan, Pipeline, Extract, Ingest, Group, Check, Generate, Llm Audit, Docs, Decompose, Infrastructure, Trace Requirements

### Assess (src-mcp-COMP-2)

**Files:**
- `src/opencode_arch/mcp/tools/assess.py`
**Downstream dependents (must re-test):** Slice, Quality

### Author (src-mcp-COMP-3)

**Files:**
- `src/opencode_arch/mcp/tools/author.py`
**Downstream dependents (must re-test):** Slice, Quality

### Check (src-mcp-COMP-4)

**Files:**
- `src/opencode_arch/mcp/tools/check.py`
**Downstream dependents (must re-test):** Slice, Quality

### Correct (src-mcp-COMP-5)

**Files:**
- `src/opencode_arch/mcp/tools/correct.py`
**Downstream dependents (must re-test):** Slice, Quality

### Decompose (src-mcp-COMP-6)

**Files:**
- `src/opencode_arch/mcp/tools/decompose.py`
**Downstream dependents (must re-test):** Slice, Quality

### Diff (src-mcp-COMP-7)

**Files:**
- `src/opencode_arch/mcp/tools/diff.py`
**Downstream dependents (must re-test):** Slice, Quality, Sync

### Docs (src-mcp-COMP-8)

**Files:**
- `src/opencode_arch/mcp/tools/docs.py`
**Downstream dependents (must re-test):** Slice, Quality

### Evaluate (src-mcp-COMP-9)

**Files:**
- `src/opencode_arch/mcp/tools/evaluate.py`
**Downstream dependents (must re-test):** Slice, Quality

### Export (src-mcp-COMP-10)

**Files:**
- `src/opencode_arch/mcp/tools/export.py`
**Downstream dependents (must re-test):** Slice, Quality

### Extract (src-mcp-COMP-11)

**Files:**
- `src/opencode_arch/mcp/tools/extract.py`
**Downstream dependents (must re-test):** Trace Requirements, Slice, Quality

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
**Downstream dependents (must re-test):** Slice, Quality

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
**Downstream dependents (must re-test):** Quality, Slice

### Log (src-mcp-COMP-19)

**Files:**
- `src/opencode_arch/mcp/tools/log.py`
**Downstream dependents (must re-test):** Slice, Quality

### Pipeline (src-mcp-COMP-20)

**Files:**
- `src/opencode_arch/mcp/tools/pipeline.py`
**Downstream dependents (must re-test):** Slice, Quality

### Regen Score (src-mcp-COMP-21)

**Files:**
- `src/opencode_arch/mcp/tools/regen_score.py`
**Downstream dependents (must re-test):** Quality, Slice

### Require (src-mcp-COMP-22)

**Files:**
- `src/opencode_arch/mcp/tools/require.py`
**Downstream dependents (must re-test):** Trace Requirements, Slice, Quality

### Scan (src-mcp-COMP-23)

**Files:**
- `src/opencode_arch/mcp/tools/scan.py`
**Downstream dependents (must re-test):** Slice, Quality

### Slice (src-mcp-COMP-24)

**Files:**
- `src/opencode_arch/mcp/tools/slice.py`
**Downstream dependents (must re-test):** Quality

### Stats (src-mcp-COMP-25)

**Files:**
- `src/opencode_arch/mcp/tools/stats.py`
**Downstream dependents (must re-test):** Slice, Quality

### Sync (src-mcp-COMP-26)

**Files:**
- `src/opencode_arch/mcp/tools/sync.py`
**Downstream dependents (must re-test):** Slice, Quality

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
**Downstream dependents (must re-test):** Ingest, Scan, Extract, Check, Generate, Group, Docs, Llm Audit, Decompose, Trace Requirements, Export, Pipeline

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

### Benchmark Scripts (COMP-2)

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

### LLM Integration Layer (COMP-3-2)

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
- `src/opencode_arch/cli/export_data.py`
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

---

---

## LLM Review

*Reviewed: 2026-08-18T23:32:27.941778+00:00 | Duration: 6348ms*

**Summary:** This maintenance manual is essentially a skeleton with 0% model completeness—all 57 components lack behavioral specifications, interfaces, signatures, and test contracts, rendering it unusable for actual maintenance guidance.

- The "Quality" and "Infrastructure" components are flagged HIGH impact risk yet have zero signatures or test contracts, meaning maintainers have no documented contract to verify correctness after changes.
- The CLI subsystem (Bench, Extract, Generate, Regen Loop) exhibits circular dependencies in the dependency impact table, suggesting either a modeling error or a tightly coupled design that needs refactoring.

<details>
<summary>Review details</summary>

**Prompt sent (truncated):**
```
Review the following architecture artifact 'docs/se/maintenance-manual.md'.
Respond ONLY in this format:
SUMMARY: <one paragraph overall assessment>
COMMENT: <specific observation>
COMMENT: <another observation>

---
---
document: Maintenance Manual
system: System
system_id: SYS-unknown
generated_at: 2026-08-18T23:31:29Z
generator_version: 0.3.0
model_hash: efca59bc201d
edition: 7
---

> **Model Completeness: F (0%)**
> Some sections may be empty due to missing model entities.
> - 57/57 componen
```

**Full LLM response:**
```
SUMMARY: This maintenance manual is essentially a skeleton with 0% model completeness—all 57 components lack behavioral specifications, interfaces, signatures, and test contracts, rendering it unusable for actual maintenance guidance.
COMMENT: The "Quality" and "Infrastructure" components are flagged HIGH impact risk yet have zero signatures or test contracts, meaning maintainers have no documented contract to verify correctness after changes.
COMMENT: The CLI subsystem (Bench, Extract, Generate, Regen Loop) exhibits circular dependencies in the dependency impact table, suggesting either a modeling error or a tightly coupled design that needs refactoring.
```

</details>
