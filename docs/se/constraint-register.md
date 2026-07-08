---
artifact_id: constraint-register
generated_at: 2026-07-08T18:45:06.557443+00:00
generator: opencode-arch-docs
---
# Constraint Register — opencode-arch

## Overview

This document records the non-functional requirements and design constraints governing the opencode-arch system. Each constraint is identified, classified, measured, and allocated to the component(s) it governs.

---

## Constraint Definitions

### CON-TOKENS — Token Budget Constraint

| Attribute | Value |
|-----------|-------|
| **ID** | CON-TOKENS |
| **Type** | Performance |
| **Metric** | `context_tokens` |
| **Threshold** | 4000 tokens (default, configurable) |
| **Rationale** | The core value proposition of opencode-arch is token arbitrage — compressing full repository structure into minimal context. A hard budget ensures the system delivers on this promise and prevents unbounded token consumption that would negate the efficiency gains of architecture-driven context. The threshold is configurable to allow callers to trade tokens for detail when needed. |

---

### CON-NO-HALLUCINATION — No Hallucination Constraint

| Attribute | Value |
|-----------|-------|
| **ID** | CON-NO-HALLUCINATION |
| **Type** | Reliability |
| **Metric** | `grounding_accuracy` |
| **Threshold** | 100% — all claims must trace to model/manifest |
| **Rationale** | Architecture extractions and generated documentation must be grounded exclusively in observable reality (AST manifests, validated models). Any hallucinated entities, relationships, or capabilities would corrupt downstream consumers and erode trust in the system's outputs. |

---

### CON-TIMEOUT — Runner Timeout

| Attribute | Value |
|-----------|-------|
| **ID** | CON-TIMEOUT |
| **Type** | Performance |
| **Metric** | `execution_time` |
| **Threshold** | 600 seconds per LLM call |
| **Rationale** | LLM invocations via the runner backend are unbounded by nature. A timeout prevents indefinite blocking during extraction or generation loops, ensures CLI responsiveness, and bounds resource consumption for batch benchmarking scenarios. |

---

### CON-PERMISSIONS — Cross-Directory Access

| Attribute | Value |
|-----------|-------|
| **ID** | CON-PERMISSIONS |
| **Type** | Security |
| **Metric** | `filesystem_access` |
| **Threshold** | Requires `--dangerously-skip-permissions` flag |
| **Rationale** | The system scans arbitrary repository paths and writes model files. Cross-directory access is gated behind an explicit opt-in flag to prevent unintended filesystem operations outside the target repository, enforcing the principle of least privilege by default. |

---

## Constraint Allocation

The following table maps each constraint to the component it governs:

| Constraint | Constrained Component | Component Role |
|---|---|---|
| CON-TOKENS | COMP-MCP (MCP Server) | Enforces token budget during context slicing |
| CON-NO-HALLUCINATION | COMP-CLI (CLI Commands) | Ensures extraction outputs trace to manifest/model |
| CON-TIMEOUT | COMP-RUNNER (OpenCode Runner) | Bounds execution time per LLM subprocess call |
| CON-PERMISSIONS | *(system-wide)* | Gates cross-directory filesystem access |

### Allocation Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    CLI Commands                          │
│                    (COMP-CLI)                            │
│                                                         │
│   ◄── CON-NO-HALLUCINATION                             │
│       "all claims must trace to model/manifest"         │
├─────────────┬───────────┬───────────┬───────────────────┤
│             │           │           │                   │
│             ▼           ▼           ▼                   │
│      COMP-RUNNER  COMP-TELEMETRY  COMP-PROMPTS         │
│                                                         │
│   ◄── CON-TIMEOUT                                      │
│       "600s per LLM call"                              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    MCP Server                            │
│                    (COMP-MCP)                            │
│                                                         │
│   ◄── CON-TOKENS                                       │
│       "4000 tokens default"                            │
│                                                         │
│             │                                           │
│             ▼                                           │
│      IF-ARCH-MODEL (consumes)                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    Learning Loop                         │
│                    (COMP-LEARNING)                       │
│                                                         │
│             │                                           │
│             ▼                                           │
│      COMP-TELEMETRY (depends-on)                       │
└─────────────────────────────────────────────────────────┘
```

### Dependency Context

Constraints propagate through the dependency graph. The following dependencies are relevant to constraint enforcement:

- **COMP-CLI** depends on COMP-RUNNER — timeout constraint (CON-TIMEOUT) on the runner directly affects CLI extraction and generation loops.
- **COMP-CLI** depends on COMP-TELEMETRY — telemetry records constraint adherence (token usage, execution time).
- **COMP-CLI** depends on COMP-LEARNING — learning loop consumes telemetry to optimize future token budgets within CON-TOKENS bounds.
- **COMP-CLI** depends on COMP-PROMPTS — prompt templates are sized to respect CON-TOKENS when combined with context.
- **COMP-MCP** consumes IF-ARCH-MODEL — token budget (CON-TOKENS) governs how much of the model is materialized into context.
- **COMP-LEARNING** depends on COMP-TELEMETRY — learning uses recorded metrics to detect constraint violations over time.

---

## Enforcement Mechanisms

| Constraint | Enforcement Point | Mechanism |
|---|---|---|
| CON-TOKENS | `architect_slice()` | `budget` parameter with default 4000; slicer truncates output to fit |
| CON-NO-HALLUCINATION | `run_extract()` loop | Validation score gates storage; model must parse against manifest |
| CON-TIMEOUT | `OpencodeRunner.run()` | Subprocess timeout parameter; raises on expiry |
| CON-PERMISSIONS | CLI argument parser | Flag must be explicitly passed; default denies cross-directory access |
