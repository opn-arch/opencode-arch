---
document: Maintenance Manual
system: Src (mcp)
system_id: SYS-unknown
generated_at: 2026-08-18T12:58:38Z
generator_version: 0.3.0
model_hash: 5baae539a353
edition: 13
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
| Quality | Correct, Regen Score, Diff, Scan, Decompose, Pipeline, Ingest, Evaluate, Learn, Stats, Validate, Extract, Assess, Export, Docs, Generate, Group, Feedback, Trace Requirements, Require, Slice, Llm Audit, Author, Sync, Gate, Log, Check | Decompose, Export, Pipeline, Infrastructure, Group, Check, Ingest, Scan, Generate, Extract, Trace Requirements, Docs, Llm Audit | HIGH |
| Assess | — | Quality, Slice | MEDIUM |
| Author | — | Slice, Quality | MEDIUM |
| Check | Quality, Infrastructure | Slice, Quality | MEDIUM |
| Correct | — | Quality, Slice | MEDIUM |
| Decompose | Quality, Infrastructure | Quality, Slice | MEDIUM |
| Diff | — | Quality, Slice, Sync | MEDIUM |
| Docs | Infrastructure, Quality | Quality, Slice | MEDIUM |
| Evaluate | — | Quality, Slice | MEDIUM |
| Export | Quality, Infrastructure | Quality, Slice | MEDIUM |
| Extract | Infrastructure, Quality | Trace Requirements, Quality, Slice | MEDIUM |
| Feedback | — | Quality, Slice | MEDIUM |
| Gate | — | Slice, Quality | MEDIUM |
| Generate | Infrastructure, Quality | Slice, Quality | MEDIUM |
| Group | Quality, Infrastructure | Quality, Slice | MEDIUM |
| Ingest | Quality, Infrastructure | Quality, Slice | MEDIUM |
| Learn | — | Quality, Slice | MEDIUM |
| Llm Audit | Infrastructure, Quality | Slice, Quality | MEDIUM |
| Log | — | Slice, Quality | MEDIUM |
| Pipeline | Quality, Infrastructure | Quality, Slice | MEDIUM |
| Regen Score | — | Quality, Slice | MEDIUM |
| Require | — | Quality, Trace Requirements, Slice | MEDIUM |
| Scan | Quality, Infrastructure | Quality, Slice | MEDIUM |
| Slice | Llm Audit, Author, Sync, Gate, Log, Regen Score, Diff, Scan, Decompose, Pipeline, Ingest, Evaluate, Learn, Generate, Stats, Validate, Extract, Assess, Export, Docs, Group, Feedback, Trace Requirements, Require, Check, Correct | Quality | LOW |
| Stats | — | Quality, Slice | MEDIUM |
| Sync | Diff | Slice, Quality | MEDIUM |
| Trace Requirements | Extract, Infrastructure, Require, Quality | Quality, Slice | MEDIUM |
| Validate | — | Quality, Slice | MEDIUM |
| Infrastructure | Quality | Generate, Llm Audit, Extract, Trace Requirements, Docs, Decompose, Check, Export, Ingest, Pipeline, Group, Scan | HIGH |

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Quality (src-mcp-COMP-1)

**Files:**
- `src/opencode_arch/mcp/quality.py`
**Downstream dependents (must re-test):** Decompose, Export, Pipeline, Infrastructure, Group, Check, Ingest, Scan, Generate, Extract, Trace Requirements, Docs, Llm Audit

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
**Downstream dependents (must re-test):** Slice, Quality

### Correct (src-mcp-COMP-5)

**Files:**
- `src/opencode_arch/mcp/tools/correct.py`
**Downstream dependents (must re-test):** Quality, Slice

### Decompose (src-mcp-COMP-6)

**Files:**
- `src/opencode_arch/mcp/tools/decompose.py`
**Downstream dependents (must re-test):** Quality, Slice

### Diff (src-mcp-COMP-7)

**Files:**
- `src/opencode_arch/mcp/tools/diff.py`
**Downstream dependents (must re-test):** Quality, Slice, Sync

### Docs (src-mcp-COMP-8)

**Files:**
- `src/opencode_arch/mcp/tools/docs.py`
**Downstream dependents (must re-test):** Quality, Slice

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
**Downstream dependents (must re-test):** Trace Requirements, Quality, Slice

### Feedback (src-mcp-COMP-12)

**Files:**
- `src/opencode_arch/mcp/tools/feedback.py`
**Downstream dependents (must re-test):** Quality, Slice

### Gate (src-mcp-COMP-13)

**Files:**
- `src/opencode_arch/mcp/tools/gate.py`
**Downstream dependents (must re-test):** Slice, Quality

### Generate (src-mcp-COMP-14)

**Files:**
- `src/opencode_arch/mcp/tools/generate.py`
**Downstream dependents (must re-test):** Slice, Quality

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
**Downstream dependents (must re-test):** Quality, Slice

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
**Downstream dependents (must re-test):** Quality, Trace Requirements, Slice

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
**Downstream dependents (must re-test):** Slice, Quality

### Trace Requirements (src-mcp-COMP-27)

**Files:**
- `src/opencode_arch/mcp/tools/trace_requirements.py`
**Downstream dependents (must re-test):** Quality, Slice

### Validate (src-mcp-COMP-28)

**Files:**
- `src/opencode_arch/mcp/tools/validate.py`
**Downstream dependents (must re-test):** Quality, Slice

### Infrastructure (src-mcp-COMP-29)

**Files:**
- `src/opencode_arch/mcp/__main__.py`
- `src/opencode_arch/mcp/server.py`
**Downstream dependents (must re-test):** Generate, Llm Audit, Extract, Trace Requirements, Docs, Decompose, Check, Export, Ingest, Pipeline, Group, Scan

## Known Constraints

*No constraint allocations defined.*
