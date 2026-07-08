---
artifact_id: component-catalog
generated_at: 2026-07-08T18:43:27.241922+00:00
generator: opencode-arch-docs
---
# Component Reference Catalog

## Overview

This catalog documents all components in the opencode-arch system, their classifications, responsibilities, and interdependencies.

---

## Components

### COMP-CLI: CLI Commands

| Property | Value |
|----------|-------|
| **ID** | COMP-CLI |
| **Kind** | module |
| **Layer** | LAYER-CLI |
| **Status** | ACTIVE |

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

**Responsibilities:**
- Parse CLI arguments
- Orchestrate extraction, generation, regen-loop, docs workflows
- Display results to user

---

### COMP-MCP: MCP Server

| Property | Value |
|----------|-------|
| **ID** | COMP-MCP |
| **Kind** | service |
| **Layer** | LAYER-MCP |
| **Status** | ACTIVE |

**Files:**
- `src/opencode_arch/mcp/__main__.py`
- `src/opencode_arch/mcp/server.py`
- `src/opencode_arch/mcp/tools/scan.py`
- `src/opencode_arch/mcp/tools/slice.py`
- `src/opencode_arch/mcp/tools/validate.py`
- `src/opencode_arch/mcp/tools/extract.py`
- `src/opencode_arch/mcp/tools/generate.py`

**Responsibilities:**
- Expose architecture tools via MCP protocol
- Compress context within token budget
- Bridge between LLM agent and architecture-model-standard

---

### COMP-RUNNER: OpenCode Runner

| Property | Value |
|----------|-------|
| **ID** | COMP-RUNNER |
| **Kind** | library |
| **Layer** | LAYER-RUNNER |
| **Status** | ACTIVE |

**Files:**
- `src/opencode_arch/runner/base.py`
- `src/opencode_arch/runner/opencode.py`

**Responsibilities:**
- Invoke opencode run as subprocess
- Handle timeouts and errors
- Return structured RunResult

---

### COMP-LEARNING: Learning Loop

| Property | Value |
|----------|-------|
| **ID** | COMP-LEARNING |
| **Kind** | module |
| **Layer** | LAYER-LEARNING |
| **Status** | ACTIVE |

**Files:**
- `src/opencode_arch/learning/classifier.py`
- `src/opencode_arch/learning/adapter.py`
- `src/opencode_arch/learning/assessor.py`
- `src/opencode_arch/learning/lessons.py`
- `src/opencode_arch/learning/maintainer.py`
- `src/opencode_arch/learning/patterns.py`

**Responsibilities:**
- Classify test failure patterns
- Adapt prompts based on patterns
- Generate report cards with grades
- Extract and store lessons
- Detect documentation drift

---

### COMP-TELEMETRY: Telemetry Store

| Property | Value |
|----------|-------|
| **ID** | COMP-TELEMETRY |
| **Kind** | data-store |
| **Layer** | LAYER-TELEMETRY |
| **Status** | ACTIVE |

**Files:**
- `src/opencode_arch/telemetry/store.py`
- `src/opencode_arch/telemetry/recorder.py`

**Responsibilities:**
- Persist tool invocation metrics
- Store regen outcomes and learning data
- Provide query interface for metrics display

---

### COMP-PROMPTS: Prompt Templates

| Property | Value |
|----------|-------|
| **ID** | COMP-PROMPTS |
| **Kind** | library |
| **Layer** | LAYER-CLI |
| **Status** | ACTIVE |

**Files:**
- `src/opencode_arch/prompts/regen.py`
- `src/opencode_arch/prompts/extract.py`

**Responsibilities:**
- Define LLM prompt templates
- Structure system/user prompts for extraction and regen

---

## Component Dependencies

### Direct Dependencies

| Source | Target | Relationship |
|--------|--------|--------------|
| COMP-CLI | COMP-RUNNER | depends-on |
| COMP-CLI | COMP-TELEMETRY | depends-on |
| COMP-CLI | COMP-LEARNING | depends-on |
| COMP-CLI | COMP-PROMPTS | depends-on |
| COMP-MCP | IF-ARCH-MODEL | consumes |
| COMP-LEARNING | COMP-TELEMETRY | depends-on |

### Capability Realizations

| Component | Capability | Relationship |
|-----------|------------|--------------|
| COMP-CLI | CAP-EXTRACT | realizes |
| COMP-CLI | CAP-GENERATE | realizes |
| COMP-CLI | CAP-DOCS | realizes |
| COMP-CLI | CAP-REGEN | realizes |
| COMP-MCP | CAP-MCP | realizes |
| COMP-LEARNING | CAP-LEARN | realizes |
| COMP-TELEMETRY | CAP-TELEMETRY | realizes |

### Constraints Applied

| Constraint | Target | Relationship |
|------------|--------|--------------|
| CON-TOKENS | COMP-MCP | constrained-by |
| CON-NO-HALLUCINATION | COMP-CLI | constrained-by |
| CON-TIMEOUT | COMP-RUNNER | constrained-by |

---

## Dependency Summary

**COMP-CLI** is the primary orchestrator, depending on four other components: COMP-RUNNER for subprocess execution, COMP-TELEMETRY for metrics persistence, COMP-LEARNING for adaptive behavior, and COMP-PROMPTS for LLM prompt construction.

**COMP-MCP** operates independently of the CLI layer, consuming the external IF-ARCH-MODEL interface directly.

**COMP-LEARNING** has a single dependency on COMP-TELEMETRY for storing and retrieving pattern data.

**COMP-RUNNER**, **COMP-TELEMETRY**, and **COMP-PROMPTS** are leaf components with no internal dependencies.
