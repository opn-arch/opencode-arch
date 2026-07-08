---
artifact_id: system-overview
generated_at: 2026-07-08T18:43:53.927933+00:00
generator: opencode-arch-docs
---
# System Overview: OpenCode Architecture Extension

## Project

**Project:** opencode-arch
**Schema Version:** 1.4
**Generated:** 2026-07-08

The OpenCode Architecture Extension (opencode-arch) is an MCP server and CLI toolset that provides context compression tools for LLM agents working with software codebases. It enables architecture-driven development by compressing repository structure into minimal token representations, allowing frontier models to reason about codebases with reduced token expenditure.

## Architecture

The system is organized into five layers, ordered by proximity to the user:

| Layer | Technology | Purpose |
|-------|-----------|---------|
| CLI Layer | argparse, asyncio | User-facing command interface |
| MCP Server Layer | FastMCP, mcp-protocol | Agent-facing tool interface |
| Learning Layer | dataclasses, regex | Pattern classification and prompt adaptation |
| Runner Layer | subprocess, Protocol | External process invocation |
| Telemetry Layer | SQLite | Metrics persistence and querying |

The CLI and MCP layers serve as the two primary entry points — one for human developers, one for LLM agents. Both delegate downward to the Runner, Learning, and Telemetry layers for execution, intelligence, and observability respectively.

## Key Components

### CLI Commands
- **Type:** Module
- **Layer:** CLI Layer
- **Technology:** argparse
- **Role:** Parses command-line arguments and orchestrates the extraction, generation, regen-loop, and documentation workflows. Displays results to the user.
- **Key files:** `src/opencode_arch/cli/main.py`, `src/opencode_arch/cli/extract.py`, `src/opencode_arch/cli/generate.py`, `src/opencode_arch/cli/bench.py`, `src/opencode_arch/cli/regen_loop.py`, `src/opencode_arch/cli/docs.py`

### MCP Server
- **Type:** Service
- **Layer:** MCP Server Layer
- **Technology:** FastMCP
- **Role:** Exposes architecture tools via the MCP protocol. Compresses context within token budgets and bridges between the LLM agent and the architecture-model-standard library.
- **Key files:** `src/opencode_arch/mcp/server.py`, `src/opencode_arch/mcp/tools/scan.py`, `src/opencode_arch/mcp/tools/slice.py`, `src/opencode_arch/mcp/tools/validate.py`, `src/opencode_arch/mcp/tools/extract.py`

### Prompt Templates
- **Type:** Library
- **Layer:** CLI Layer
- **Technology:** Python strings
- **Role:** Defines structured LLM prompt templates for extraction and regeneration workflows.
- **Key files:** `src/opencode_arch/prompts/regen.py`, `src/opencode_arch/prompts/extract.py`

### Learning Loop
- **Type:** Module
- **Layer:** Learning Layer
- **Technology:** dataclasses, regex
- **Role:** Classifies test failure patterns, adapts prompts based on observed patterns, generates report cards with grades, extracts and stores lessons, and detects documentation drift.
- **Key files:** `src/opencode_arch/learning/classifier.py`, `src/opencode_arch/learning/adapter.py`, `src/opencode_arch/learning/assessor.py`, `src/opencode_arch/learning/lessons.py`

### OpenCode Runner
- **Type:** Library
- **Layer:** Runner Layer
- **Technology:** subprocess, Protocol
- **Role:** Invokes `opencode run` as a subprocess, handles timeouts and errors, and returns structured `RunResult` objects.
- **Key files:** `src/opencode_arch/runner/base.py`, `src/opencode_arch/runner/opencode.py`

### Telemetry Store
- **Type:** Data Store
- **Layer:** Telemetry Layer
- **Technology:** SQLite
- **Role:** Persists tool invocation metrics, stores regeneration outcomes and learning data, and provides a query interface for metrics display.
- **Key files:** `src/opencode_arch/telemetry/store.py`, `src/opencode_arch/telemetry/recorder.py`

## Component Interactions

The system's components interact through well-defined dependency relationships:

**CLI as orchestrator:** The CLI Commands component serves as the primary orchestrator, depending on four other components:
- It invokes the **OpenCode Runner** to delegate reasoning tasks to the LLM agent via subprocess.
- It reads from and writes to the **Telemetry Store** to record metrics and display results.
- It leverages the **Learning Loop** to classify failures, adapt prompts, and improve over iterations.
- It uses **Prompt Templates** to construct structured prompts for extraction and regeneration workflows.

**MCP as agent interface:** The MCP Server consumes the **Architecture Model API** (an external interface provided by the architecture-model-standard library) to offer compressed context and validation to LLM agents.

**Learning feedback loop:** The Learning Loop depends on the **Telemetry Store** to read historical outcomes and persist lessons learned, enabling prompt adaptation based on accumulated experience.

## Constraints

The system operates under three documented constraints:

| Constraint | Applies To | Description |
|-----------|-----------|-------------|
| Token Budget | MCP Server | Context compression must stay within the specified token budget |
| No Hallucination | CLI Commands | Outputs must be grounded in actual repository content |
| Timeout | OpenCode Runner | Subprocess invocations must respect timeout limits |

## Capabilities

The system realizes the following capabilities:

- **Architecture Extraction** (CLI Commands) — Extract architecture models from repositories
- **Code Generation** (CLI Commands) — Generate code with test verification
- **Documentation** (CLI Commands) — Generate and validate documentation
- **Regeneration Loop** (CLI Commands) — Iterative improvement of generated artifacts
- **MCP Tool Exposure** (MCP Server) — Provide tools to LLM agents via protocol
- **Learning** (Learning Loop) — Classify patterns and adapt behavior
- **Telemetry** (Telemetry Store) — Record and query operational metrics
