---
artifact_id: capability-map
generated_at: 2026-07-08T18:43:05.147925+00:00
generator: opencode-arch-docs
---
# Capability Map — opencode-arch

## Overview

This document maps each system capability to its priority, functional block, realizing components, and supporting dependencies.

## Capabilities

### CAP-EXTRACT — Architecture Extraction

| Attribute | Value |
|-----------|-------|
| Priority | High |
| Functional Block | F1 |
| Realized by | CLI Commands |
| Dependencies | OpenCode Runner, Telemetry Store, Learning Loop, Prompt Templates |
| Constraints | CON-NO-HALLUCINATION |

Extracts architecture models from target repositories by orchestrating the runner with structured prompts and recording results via telemetry.

---

### CAP-GENERATE — Code Generation

| Attribute | Value |
|-----------|-------|
| Priority | High |
| Functional Block | F1 |
| Realized by | CLI Commands |
| Dependencies | OpenCode Runner, Telemetry Store, Learning Loop, Prompt Templates |
| Constraints | CON-NO-HALLUCINATION |

Generates code artifacts from architecture models, delegating inference to the runner backend and validating outputs against test suites.

---

### CAP-DOCS — SE Document Generation

| Attribute | Value |
|-----------|-------|
| Priority | High |
| Functional Block | F1 |
| Realized by | CLI Commands |
| Dependencies | OpenCode Runner, Telemetry Store, Learning Loop, Prompt Templates |
| Constraints | CON-NO-HALLUCINATION |

Produces software engineering documentation artifacts from architecture context and repository structure.

---

### CAP-REGEN — Subsystem Regen-Loop

| Attribute | Value |
|-----------|-------|
| Priority | High |
| Functional Block | F1 |
| Realized by | CLI Commands |
| Dependencies | OpenCode Runner, Telemetry Store, Learning Loop, Prompt Templates |
| Constraints | CON-NO-HALLUCINATION |

Iteratively regenerates subsystem code until quality gates (test pass rate, validation score) are satisfied.

---

### CAP-MCP — MCP Tool Serving

| Attribute | Value |
|-----------|-------|
| Priority | High |
| Functional Block | F4 |
| Realized by | MCP Server |
| Consumes | Architecture Model API |
| Constraints | CON-TOKENS |

Serves the five architecture tools (scan, slice, validate, extract, generate) over the MCP protocol to LLM agents.

---

### CAP-LEARN — Learning Loop

| Attribute | Value |
|-----------|-------|
| Priority | Medium |
| Functional Block | F3 |
| Realized by | Learning Loop |
| Dependencies | Telemetry Store |

Analyzes historical telemetry to optimize context budgets and prompt strategies over time.

---

### CAP-TELEMETRY — Telemetry & Metrics

| Attribute | Value |
|-----------|-------|
| Priority | Medium |
| Functional Block | F7 |
| Realized by | Telemetry Store |

Records tool invocations, context token counts, output quality scores, and iteration counts to a persistent store.

---

## Realization Summary

| Capability | Realizing Component | Priority |
|------------|-------------------|----------|
| CAP-EXTRACT | CLI Commands | High |
| CAP-GENERATE | CLI Commands | High |
| CAP-DOCS | CLI Commands | High |
| CAP-REGEN | CLI Commands | High |
| CAP-MCP | MCP Server | High |
| CAP-LEARN | Learning Loop | Medium |
| CAP-TELEMETRY | Telemetry Store | Medium |

## Component Dependency Graph

```
CLI Commands
├── depends-on → OpenCode Runner
├── depends-on → Telemetry Store
├── depends-on → Learning Loop
└── depends-on → Prompt Templates

MCP Server
└── consumes → Architecture Model API

Learning Loop
└── depends-on → Telemetry Store
```

## Constraints

| Constraint | Applies To | Description |
|------------|-----------|-------------|
| CON-TOKENS | MCP Server | Token budget limits on context slicing |
| CON-NO-HALLUCINATION | CLI Commands | Output must be grounded in repository evidence |
| CON-TIMEOUT | OpenCode Runner | Execution time limits on runner invocations |
