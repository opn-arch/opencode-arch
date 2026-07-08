---
artifact_id: integration-guide
generated_at: 2026-07-08T18:48:41.533157+00:00
generator: opencode-arch-docs
---
# Integration Guide — opencode-arch

## Overview

This document describes the available interfaces, integration patterns, and constraints for developers connecting to the opencode-arch system. It covers both the MCP tool protocol (for LLM agents) and the CLI/library interfaces (for human developers and automation).

---

## Available Interfaces

| Interface | Type | Protocol | Provider | Consumer | Endpoints |
|-----------|------|----------|----------|----------|-----------|
| IF-CLI | Internal | argparse | CLI Commands | Developer | 6 |
| IF-MCP | External | MCP stdio | MCP Server | LLM Agent | 5 |
| IF-RUNNER | Internal | subprocess | OpenCode Runner | CLI Commands | 1 |
| IF-TELEMETRY | Internal | SQLite | Telemetry Store | CLI Commands | 3 |
| IF-ARCH-MODEL | Internal | Python import | OpenCode Runner | CLI Commands | 4 |

### IF-MCP — MCP Tool Protocol

- **Protocol:** MCP stdio (JSON-RPC over stdin/stdout)
- **Direction:** External — consumed by LLM agents
- **Endpoints:** 5 tools (`architect_scan`, `architect_slice`, `architect_validate`, `architect_extract`, `architect_generate`)
- **Data format:** JSON request/response per MCP specification

### IF-CLI — CLI Interface

- **Protocol:** argparse
- **Direction:** Internal — consumed by developers
- **Endpoints:** 6 commands (`extract`, `generate`, `bench`, `metrics`, `regen-loop`, `docs`)
- **Data format:** Command-line arguments and flags; output to stdout

### IF-RUNNER — Runner Backend Protocol

- **Protocol:** subprocess
- **Direction:** Internal — consumed by CLI Commands
- **Endpoints:** 1 (`run`)
- **Data format:** Structured `RunResult` (output string, exit code, success boolean)

### IF-TELEMETRY — Telemetry Store Interface

- **Protocol:** SQLite
- **Direction:** Internal — consumed by CLI Commands
- **Endpoints:** 3 (record invocation, query metrics, store regen outcomes)
- **Data format:** SQLite rows; accessed via Python API

### IF-ARCH-MODEL — Architecture Model API

- **Protocol:** Python import
- **Direction:** Internal — provided by OpenCode Runner process
- **Endpoints:** 4 (manifest generation, model parsing, validation, context slicing)
- **Data format:** Python objects; YAML serialization for persistence

---

## Integration Patterns

### Integrating with the MCP Server (COMP-MCP)

**Layer:** MCP Server Layer  
**Technology:** FastMCP  
**Status:** ACTIVE

**Files:**
- `src/opencode_arch/mcp/__main__.py`
- `src/opencode_arch/mcp/server.py`
- `src/opencode_arch/mcp/tools/scan.py`
- `src/opencode_arch/mcp/tools/slice.py`
- `src/opencode_arch/mcp/tools/validate.py`
- `src/opencode_arch/mcp/tools/extract.py`
- `src/opencode_arch/mcp/tools/generate.py`

**Recommended pattern:** Connect via MCP stdio transport. The server exposes five tools that compress repository context within token budgets, bridging between the LLM agent and the `architecture-model-standard` library. Tools are stateless per-call; the agent orchestrates multi-step workflows (scan → slice → validate → extract).

**Responsibilities:**
- Expose architecture tools via MCP protocol
- Compress context within token budget
- Bridge between LLM agent and architecture-model-standard

---

### Integrating with CLI Commands (COMP-CLI)

**Layer:** CLI Layer  
**Technology:** argparse  
**Status:** ACTIVE

**Files:**
- `src/opencode_arch/cli/main.py`
- `src/opencode_arch/cli/extract.py`
- `src/opencode_arch/cli/generate.py`
- `src/opencode_arch/cli/bench.py`
- `src/opencode_arch/cli/regen_loop.py`
- `src/opencode_arch/cli/docs.py`
- `src/opencode_arch/cli/docs_validator.py`
- `src/opencode_arch/cli/metrics.py`
- `src/opencode_arch/cli/gap_analyzer.py`

**Recommended pattern:** Invoke via the `opencode-arch` command. The CLI orchestrates extraction, generation, regen-loop, and docs workflows by composing the Runner, Telemetry, Learning, and Prompt components. Extend by adding new subcommands in the CLI layer that follow the existing orchestration pattern.

**Responsibilities:**
- Parse CLI arguments
- Orchestrate extraction, generation, regen-loop, docs workflows
- Display results to user

**Dependencies:** COMP-RUNNER, COMP-TELEMETRY, COMP-LEARNING, COMP-PROMPTS

---

### Integrating with the OpenCode Runner (COMP-RUNNER)

**Layer:** Runner Layer  
**Technology:** subprocess  
**Status:** ACTIVE

**Files:**
- `src/opencode_arch/runner/base.py`
- `src/opencode_arch/runner/opencode.py`

**Recommended pattern:** Implement the `RunnerBackend` protocol to provide a custom model backend. The protocol requires a single `run(prompt, repo_path) -> RunResult` method. The default `OpencodeRunner` invokes `opencode run` as a subprocess. Swap implementations by conforming to the protocol interface defined in `base.py`.

**Responsibilities:**
- Invoke `opencode run` as subprocess
- Handle timeouts and errors
- Return structured `RunResult`

---

### Integrating with the Learning Loop (COMP-LEARNING)

**Layer:** Learning Layer  
**Technology:** dataclasses  
**Status:** ACTIVE

**Files:**
- `src/opencode_arch/learning/classifier.py`
- `src/opencode_arch/learning/adapter.py`
- `src/opencode_arch/learning/assessor.py`
- `src/opencode_arch/learning/lessons.py`
- `src/opencode_arch/learning/maintainer.py`
- `src/opencode_arch/learning/patterns.py`

**Recommended pattern:** The learning loop is consumed by the CLI layer. It classifies test failure patterns, adapts prompts based on observed patterns, generates report cards with grades, extracts and stores lessons, and detects documentation drift. Integrate by passing test results through the classifier and using the adapter to refine prompts on subsequent iterations.

**Responsibilities:**
- Classify test failure patterns
- Adapt prompts based on patterns
- Generate report cards with grades
- Extract and store lessons
- Detect documentation drift

**Dependencies:** COMP-TELEMETRY

---

### Integrating with Telemetry (COMP-TELEMETRY)

**Layer:** Telemetry Layer  
**Technology:** SQLite  
**Status:** ACTIVE

**Files:**
- `src/opencode_arch/telemetry/store.py`
- `src/opencode_arch/telemetry/recorder.py`

**Recommended pattern:** Use the `TelemetryStore` class for direct database access or the `record_invocation()` async function for fire-and-forget recording. Telemetry persists tool invocation metrics, regen outcomes, and learning data. Query via the store interface for metrics display or analysis.

**Responsibilities:**
- Persist tool invocation metrics
- Store regen outcomes and learning data
- Provide query interface for metrics display

---

### Integrating with Prompt Templates (COMP-PROMPTS)

**Layer:** CLI Layer  
**Technology:** Python strings  
**Status:** ACTIVE

**Files:**
- `src/opencode_arch/prompts/regen.py`
- `src/opencode_arch/prompts/extract.py`

**Recommended pattern:** Import prompt templates directly. Templates define structured system/user prompts for extraction and regen workflows. Customize by extending the template strings or passing additional context variables.

**Responsibilities:**
- Define LLM prompt templates
- Structure system/user prompts for extraction and regen

---

## Component Dependency Graph

```
Developer ──► CLI Commands
                 ├──► OpenCode Runner ──► (subprocess: opencode run)
                 ├──► Telemetry Store ──► (SQLite database)
                 ├──► Learning Loop ──► Telemetry Store
                 └──► Prompt Templates

LLM Agent ──► MCP Server ──► Architecture Model API (Python import)
```

---

## Security Constraints & Authentication

### CON-PERMISSIONS — Cross-Directory Access

- **Type:** Security
- **Metric:** filesystem_access
- **Requirement:** Accessing repositories outside the current working directory requires the `--dangerously-skip-permissions` flag. Without this flag, the system restricts filesystem operations to the immediate project directory.
- **Recommendation:** Only use this flag in trusted automation environments. Never pass it in user-facing scripts without explicit consent.

### CON-NO-HALLUCINATION — No Hallucination Constraint

- **Type:** Reliability
- **Metric:** grounding_accuracy
- **Threshold:** 100%
- **Requirement:** All claims produced by the system must trace back to the model or manifest. The system does not fabricate architecture entities or relationships not grounded in source analysis.
- **Implication for integrators:** Do not assume tool outputs contain speculative information. All returned data is derived from AST scanning or validated model content.

---

## Performance Constraints

### CON-TOKENS — Token Budget Constraint

- **Type:** Performance
- **Metric:** context_tokens
- **Default threshold:** 4000 tokens
- **Configurable:** Yes — pass `budget` parameter to `architect_slice`
- **Recommendation:** Start with the default 4000 token budget. Increase only if extraction quality is insufficient for complex repositories. Monitor via telemetry to find optimal budgets per repository size.

### CON-TIMEOUT — Runner Timeout

- **Type:** Performance
- **Metric:** execution_time
- **Threshold:** 600 seconds per LLM call
- **Requirement:** Each invocation of the runner backend (subprocess call to `opencode run`) must complete within 600 seconds. Calls exceeding this threshold are terminated.
- **Recommendation:** For large repositories, consider reducing the scope of extraction (use `focus` parameter) rather than increasing timeout.

---

## Summary of Integration Points

| Use Case | Interface | Protocol | Key Constraint |
|----------|-----------|----------|----------------|
| LLM agent consuming architecture tools | IF-MCP | MCP stdio | Token budget (4000 default) |
| Developer running extractions | IF-CLI | argparse | Runner timeout (600s) |
| Custom model backend | IF-RUNNER | subprocess | RunnerBackend protocol conformance |
| Metrics and analytics | IF-TELEMETRY | SQLite | Read-only queries recommended |
| Extending architecture analysis | IF-ARCH-MODEL | Python import | No hallucination constraint |
