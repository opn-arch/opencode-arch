---
document: Maintenance Manual
system: opencode-arch
system_id: SYS-unknown
generated_at: 2026-08-17T18:14:32Z
generator_version: 0.3.0
model_hash: b8b11e54f9db
edition: 1
---

# Maintenance Manual: opencode-arch

## Component Inventory

| Component | Kind | Layer | Files | Signatures | Test Contracts |
|-----------|------|-------|-------|-----------|----------------|
| Extraction Tools (COMP-1) | service | — | 5 | 0 | 0 |
| Artifacts (COMP-2) | service | — | 4 | 0 | 0 |
| CLI Commands (COMP-3) | service | — | 13 | 0 | 25 |
| Requirements (COMP-4) | service | — | 5 | 0 | 0 |
| Resolution (COMP-5) | service | — | 6 | 0 | 21 |
| Context Tools (COMP-6) | service | — | 3 | 0 | 0 |
| Model Management Tools (COMP-7) | service | — | 4 | 0 | 0 |
| Documentation Tools (COMP-8) | service | — | 3 | 0 | 0 |
| Quality Gate Tools (COMP-9) | service | — | 4 | 0 | 0 |
| Requirements Tools (COMP-10) | service | — | 3 | 0 | 0 |
| Live Analysis Tools (COMP-11) | service | — | 5 | 0 | 0 |
| Runner (COMP-12) | service | — | 2 | 0 | 0 |
| Telemetry (COMP-13) | service | — | 3 | 0 | 0 |
| Learning (COMP-14) | service | — | 6 | 0 | 0 |
| MCP Server (COMP-15) | service | — | 3 | 0 | 0 |

## Dependency Impact Analysis

*No dependency relationships defined.*

## Modification Procedures

For each component, the following files and dependencies must be considered:

### Extraction Tools (COMP-1)

**Files:**
- `src/opencode_arch/mcp/tools/scan.py`
- `src/opencode_arch/mcp/tools/extract.py`
- `src/opencode_arch/mcp/tools/group.py`
- `src/opencode_arch/mcp/tools/ingest.py`
- `src/opencode_arch/mcp/tools/pipeline.py`

### Artifacts (COMP-2)

**Files:**
- `src/opencode_arch/artifacts/context.py`
- `src/opencode_arch/artifacts/diagrams.py`
- `src/opencode_arch/artifacts/selector.py`
- `src/opencode_arch/artifacts/templates.py`

### CLI Commands (COMP-3)

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
- `src/opencode_arch/cli/regen_loop.py`

### Requirements (COMP-4)

**Files:**
- `src/opencode_arch/llm/cache.py`
- `src/opencode_arch/requirements/llm_extractor.py`
- `src/opencode_arch/requirements/matcher.py`
- `src/opencode_arch/requirements/parser.py`
- `src/opencode_arch/requirements/retroactive.py`

### Resolution (COMP-5)

**Files:**
- `src/opencode_arch/regen/self_heal.py`
- `src/opencode_arch/regen/spot_check.py`
- `src/opencode_arch/agent/resolution.py`
- `src/opencode_arch/mcp/quality.py`
- `src/opencode_arch/context/formatter.py`
- `src/opencode_arch/context/pipeline_bridge.py`

### Context Tools (COMP-6)

**Files:**
- `src/opencode_arch/mcp/tools/slice.py`
- `src/opencode_arch/mcp/tools/check.py`
- `src/opencode_arch/mcp/tools/validate.py`

### Model Management Tools (COMP-7)

**Files:**
- `src/opencode_arch/mcp/tools/correct.py`
- `src/opencode_arch/mcp/tools/feedback.py`
- `src/opencode_arch/mcp/tools/learn.py`
- `src/opencode_arch/mcp/tools/stats.py`

### Documentation Tools (COMP-8)

**Files:**
- `src/opencode_arch/mcp/tools/docs.py`
- `src/opencode_arch/mcp/tools/export.py`
- `src/opencode_arch/mcp/tools/decompose.py`

### Quality Gate Tools (COMP-9)

**Files:**
- `src/opencode_arch/mcp/tools/gate.py`
- `src/opencode_arch/mcp/tools/generate.py`
- `src/opencode_arch/mcp/tools/llm_audit.py`
- `src/opencode_arch/mcp/tools/regen_score.py`

### Requirements Tools (COMP-10)

**Files:**
- `src/opencode_arch/mcp/tools/require.py`
- `src/opencode_arch/mcp/tools/trace_requirements.py`
- `src/opencode_arch/mcp/tools/author.py`

### Live Analysis Tools (COMP-11)

**Files:**
- `src/opencode_arch/mcp/tools/assess.py`
- `src/opencode_arch/mcp/tools/evaluate.py`
- `src/opencode_arch/mcp/tools/sync.py`
- `src/opencode_arch/mcp/tools/log.py`
- `src/opencode_arch/mcp/tools/diff.py`

### Runner (COMP-12)

**Files:**
- `src/opencode_arch/runner/base.py`
- `src/opencode_arch/runner/opencode.py`

### Telemetry (COMP-13)

**Files:**
- `src/opencode_arch/telemetry/collector.py`
- `src/opencode_arch/telemetry/recorder.py`
- `src/opencode_arch/telemetry/store.py`

### Learning (COMP-14)

**Files:**
- `src/opencode_arch/learning/adapter.py`
- `src/opencode_arch/learning/assessor.py`
- `src/opencode_arch/learning/classifier.py`
- `src/opencode_arch/learning/lessons.py`
- `src/opencode_arch/learning/maintainer.py`
- `src/opencode_arch/learning/patterns.py`

### MCP Server (COMP-15)

**Files:**
- `src/opencode_arch/mcp/server.py`
- `src/opencode_arch/mcp/__init__.py`
- `src/opencode_arch/mcp/quality.py`

## Known Constraints

*No constraint allocations defined.*
