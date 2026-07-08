---
artifact_id: deployment-view
generated_at: 2026-07-08T18:46:42.765748+00:00
generator: opencode-arch-docs
---
# Deployment View — opencode-arch

## Overview

opencode-arch deploys as two independent entry points — a CLI application and an MCP server — sharing common library layers. All components run in a single Python process (no containers, no network services beyond MCP stdio transport).

## Deployment Units

### Unit 1: CLI Application

**Layer:** CLI  
**Entry point:** `opencode-arch` command (installed via `pip install -e .`)  
**Process model:** Short-lived subprocess invocations

| Component | Kind | Files |
|-----------|------|-------|
| COMP-CLI | module | `cli/main.py`, `cli/extract.py`, `cli/generate.py`, `cli/bench.py`, `cli/regen_loop.py`, `cli/docs.py`, `cli/docs_validator.py`, `cli/metrics.py`, `cli/gap_analyzer.py` |
| COMP-PROMPTS | library | `prompts/regen.py`, `prompts/extract.py` |

**Co-deployed because:** Prompt templates are consumed exclusively by CLI orchestration commands. They share the same layer and have no independent deployment lifecycle.

**Responsibilities:**
- Parse CLI arguments and dispatch to subcommands
- Orchestrate extraction, generation, regen-loop, and docs workflows
- Structure LLM prompts for extraction and regeneration
- Display results to the user

**Runtime dependencies:** COMP-RUNNER, COMP-TELEMETRY, COMP-LEARNING

---

### Unit 2: MCP Server

**Layer:** MCP Server  
**Entry point:** `python -m opencode_arch.mcp` (stdio transport)  
**Process model:** Long-running server, one instance per OpenCode session

| Component | Kind | Files |
|-----------|------|-------|
| COMP-MCP | service | `mcp/__main__.py`, `mcp/server.py`, `mcp/tools/scan.py`, `mcp/tools/slice.py`, `mcp/tools/validate.py`, `mcp/tools/extract.py`, `mcp/tools/generate.py` |

**Responsibilities:**
- Expose 5 architecture tools via MCP protocol (scan, slice, validate, extract, generate)
- Compress repository context within token budget
- Bridge between LLM agent and architecture-model-standard library

**Runtime dependencies:** `architecture-model-standard` package (external), filesystem access to target repositories

---

### Unit 3: OpenCode Runner

**Layer:** Runner  
**Deployment:** Embedded library (no independent process)

| Component | Kind | Files |
|-----------|------|-------|
| COMP-RUNNER | library | `runner/base.py`, `runner/opencode.py` |

**Responsibilities:**
- Invoke `opencode run` as a subprocess
- Handle timeouts and errors
- Return structured `RunResult` to callers

**Consumed by:** COMP-CLI (extraction and generation workflows)

---

### Unit 4: Learning Loop

**Layer:** Learning  
**Deployment:** Embedded module (no independent process)

| Component | Kind | Files |
|-----------|------|-------|
| COMP-LEARNING | module | `learning/classifier.py`, `learning/adapter.py`, `learning/assessor.py`, `learning/lessons.py`, `learning/maintainer.py`, `learning/patterns.py` |

**Responsibilities:**
- Classify test failure patterns
- Adapt prompts based on observed patterns
- Generate report cards with grades
- Extract and store lessons from outcomes
- Detect documentation drift

**Runtime dependencies:** COMP-TELEMETRY (reads/writes learning data)

---

### Unit 5: Telemetry Store

**Layer:** Telemetry  
**Deployment:** Embedded data-store (SQLite file)  
**Storage location:** `~/.opencode-arch/telemetry.db`

| Component | Kind | Files |
|-----------|------|-------|
| COMP-TELEMETRY | data-store | `telemetry/store.py`, `telemetry/recorder.py` |

**Responsibilities:**
- Persist tool invocation metrics
- Store regen outcomes and learning data
- Provide query interface for metrics display

**Consumed by:** COMP-CLI, COMP-LEARNING

---

## Deployment Topology

```
Developer workstation
├── CLI process (transient)
│   ├── COMP-CLI + COMP-PROMPTS
│   ├── COMP-RUNNER ──→ spawns `opencode run` subprocess
│   ├── COMP-LEARNING
│   └── COMP-TELEMETRY ──→ ~/.opencode-arch/telemetry.db
│
└── MCP Server process (long-lived, stdio)
    └── COMP-MCP ──→ reads target repo filesystem
                 ──→ reads/writes .architecture-model.yaml
```

Both processes run on the same machine. They do not communicate with each other directly — the MCP server is invoked by the LLM agent (via OpenCode), while the CLI is invoked by the developer.

---

## Operational Constraints

### Performance

| Constraint | Metric | Threshold | Impact |
|------------|--------|-----------|--------|
| CON-TOKENS | `context_tokens` | 4000 tokens (default, configurable) | Slice tool must compress full repository structure within budget. Exceeding budget degrades agent reasoning quality and increases cost. |
| CON-TIMEOUT | `execution_time` | 600 seconds per LLM call | Runner subprocess enforces hard timeout. Long-running extractions are killed and reported as failures. |

### Reliability

| Constraint | Metric | Threshold | Impact |
|------------|--------|-----------|--------|
| CON-NO-HALLUCINATION | `grounding_accuracy` | 100% | All claims in extracted models must trace back to the manifest or existing model. The slice tool provides only verified context — no fabrication. |

### Security

| Constraint | Metric | Threshold | Impact |
|------------|--------|-----------|--------|
| CON-PERMISSIONS | `filesystem_access` | Requires `--dangerously-skip-permissions` flag | Cross-directory repository access (scanning repos outside the current workspace) requires explicit opt-in via permissions flag. |

---

## Failure Modes

| Scenario | Affected Unit | Behavior |
|----------|---------------|----------|
| SQLite write failure | Telemetry Store | Swallowed — telemetry failures never block tool operation |
| Runner timeout (>600s) | CLI Application | Subprocess killed, `RunResult.success = False` returned |
| Token budget exceeded | MCP Server | Context truncated to fit budget; lower fidelity output |
| `architecture-model-standard` not installed | MCP Server | Import error at startup; tools unavailable |
| Target repo not found | Both | Filesystem error returned to caller |

---

## Prerequisites

- Python 3.11+
- `architecture-model-standard` >= 0.3.0 installed
- `opencode` CLI available on PATH (for Runner subprocess calls)
- Write access to `~/.opencode-arch/` (telemetry database)
- Read access to target repository filesystem
