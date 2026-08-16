# Address Issues, Requirements, and MCP Improvements

**Date:** 2026-08-16
**Source:** 245 opencode-arch sessions analyzed, 1245 unique requirements, 24 open logs, 10 MCP tools with improvement suggestions

---

## Package 1: Fix Status Filter Bug (logs-db)

The `/api/logs?status=open` filter returns done=True logs. Fix the query.

**Files:** `app/routers/logs.py` or equivalent  
**Logs addressed:** None directly, but enables all other work

---

## Package 2: Populate Model Relationships (opencode-arch)

The model has 15 components but 0 relationships. Populate from import analysis.

**Action:**
1. Run `architect_scan` to get import edges
2. Map imports to component-to-component relationships
3. Store in `.architecture-model.yaml` relationships section

**Logs addressed:** (already closed #904, #899, #890, #872 — but relationships still empty in model)

**Expected format:**
```yaml
relationships:
- source: COMP-15  # MCP Server
  target: COMP-1   # Extraction Tools
  type: uses
- source: COMP-1
  target: COMP-5   # Resolution
  type: uses
```

---

## Package 3: MCP Tool Improvements (Top 5)

### 3a. architect_log auto-prompt (141 mentions)
- Add `auto_log_triggers` to gate tool: after git commits, after multi-file changes
- Logs: #880

### 3b. architect_slice schema/introspect mode (73 mentions)
- Add `mode=schema` returning dataclass field definitions for named types
- Add `mode=help` listing valid focus values and artifact names
- Logs: #898, #902

### 3c. architect_scan schema-dump mode (30 mentions)
- Add `mode=schema` returning output format without full AST scan
- Add `mode=introspect` showing capabilities
- Logs: #892, #893, #894

### 3d. architect_docs gap-fill (19 mentions)
- Auto-detect partial model and offer to slice missing sections
- Logs: #867

### 3e. architect_pipeline tool enforcement (13 mentions)
- Prescriptive prompt: "ALWAYS call scan→group→extract, NEVER script directly"
- Logs: #861

---

## Package 4: Extraction Pipeline Fixes

### 4a. Multi-trigger detection (#901)
- Entity decomposition only finds HTTP routes
- Add: WebSocket handlers, gRPC services, CLI commands, scheduled tasks

### 4b. Import resolution (#883)
- Module name-to-file mapping mismatch
- Fix: canonical path resolution in scan tool

### 4c. Enum discovery (#869, #866)
- RelationType.USES missing, trial-and-error needed
- Fix: document all enum values in ICD, add validation

---

## Package 5: Documentation & ICDs

### 5a. Validation spec documentation (#905)
- Document scoring formula, issue categories, check types

### 5b. architecture-model-standard external ICD (#895)
- Define the contract between opencode-arch and architecture-model-standard

### 5c. Extraction pipeline type contracts (#864)
- ICD for data flowing through scan → group → allocate → relate → emit

### 5d. functional_blocks documentation (#889)
- Document origin, config flow, how they become source_blocks

---

## Package 6: Pipeline Behavior Tuning

### 6a. Behavior filtering (#877, #879)
- Reduce from 278 to 20-40 behaviors per component
- Threshold already changed from 2→5 outgoing calls (#884)

### 6b. Grouping formula validation (#896, #897)
- Benchmark sqrt(files)*0.8 against alternatives
- Test import-affinity vs subdirectory-only

---

## Package 7: Cleanup

- #873: Remove old `docs/architecture/` output (superseded by `.architecture-models/`)
- #875: Close as "plan pipeline changes" is covered by this plan

---

## Scorecard Impact Predictions

| Metric | Current | After Pkg 2 | After Pkg 3 | After All |
|--------|---------|-------------|-------------|-----------|
| **opencode-arch structured dev score** | 1.1/5 | 1.3 | 2.5 | 3.5 |
| **opencode-arch integration gaps** | 214 | 180 | 80 | 30 |
| **opencode-arch missing modes** | 111 | 111 | 40 | 15 |
| **Model check score** | 80.7% | 92% | 92% | 95% |
| **Boundary coherence** | 22.9% | 55% | 55% | 60% |
| **logs-db ingestion quality** | 2.9/5 | 2.9 | 3.2 | 3.8 |
| **logs-db child log quality** | 2.0/5 | 2.0 | 2.5 | 3.2 |

### Reasoning:

1. **Structured dev score 1.1 → 3.5**: Currently low because tools aren't called in sessions. Pkg 3 (auto-prompting, introspect modes, pipeline enforcement) directly addresses why tools go unused — they're hard to discover and don't auto-trigger.

2. **Integration gaps 214 → 30**: Relationships (Pkg 2) + tool-pipeline mapping (Pkg 3e) + ICDs (Pkg 5) close the gap between what the model knows and what the code does.

3. **Missing modes 111 → 15**: Pkg 3b/3c/3d add the specific modes that sessions kept requesting (schema, help, introspect, dry-run).

4. **Check score 80.7 → 95%**: Relationships bring relationship_accuracy from 100% (vacuously true with 0) to actually verified. Boundary coherence improves as we document cross-component contracts.

5. **Ingestion quality 2.9 → 3.8**: Pkg 1 (status filter fix) + auto-logging (Pkg 3a) means more logs are created with better metadata. Pipeline type contracts (Pkg 5c) improve structured extraction.

6. **Child log quality 2.0 → 3.2**: Auto-prompt triggers + introspect modes mean child logs get better context. Multi-trigger detection (Pkg 4a) produces richer decomposition data.

---

## Execution Order

1. **Pkg 2** (15 min) — Populate relationships from imports → immediate model improvement
2. **Pkg 3a** (30 min) — Auto-prompt for architect_log → most-requested improvement
3. **Pkg 3b** (45 min) — Slice introspect/schema modes → second most-requested
4. **Pkg 3c** (30 min) — Scan schema-dump mode
5. **Pkg 7** (5 min) — Quick cleanup
6. **Pkg 4** (2 hrs) — Pipeline fixes
7. **Pkg 5** (1 hr) — Documentation/ICDs
8. **Pkg 6** (1 hr) — Behavior tuning
9. **Pkg 1** (15 min) — logs-db status filter fix

**Total estimate:** ~6 hours
