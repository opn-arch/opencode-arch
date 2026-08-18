---
document: Maintenance Manual
system: Src (mcp)
system_id: SYS-unknown
generated_at: 2026-08-18T23:31:31Z
generator_version: 0.3.0
model_hash: 5baae539a353
edition: 5
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

## Known Constraints

*No constraint allocations defined.*
