---
document: Maintenance Manual
system: Src (mcp)
system_id: SYS-unknown
generated_at: 2026-08-18T20:07:48Z
generator_version: 0.3.0
model_hash: 5baae539a353
edition: 3
---

> **Model Completeness: F (0%)**
> Some sections may be empty due to missing model entities.
> - 29/29 components have no behavioral specification
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Maintenance Manual: Src (mcp)

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

## Known Constraints

*No constraint allocations defined.*
