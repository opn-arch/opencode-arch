---
artifact_id: layer-architecture
generated_at: 2026-07-08T18:47:58.181038+00:00
generator: opencode-arch-docs
---
# Layer Architecture — opencode-arch

## Overview

The opencode-arch system is organized into a layered architecture with three tiers. Layer ordering determines allowed dependency directions: higher-order layers (infrastructure) are consumed by lower-order layers (user-facing), ensuring clean separation of concerns.

## Layers

### Layer 1: CLI Layer (LAYER-CLI)

| Property | Value |
|----------|-------|
| **Order** | 1 (top — user-facing) |
| **Technology** | argparse, asyncio |
| **Directory** | `src/opencode_arch/cli/` |
| **Components** | CLI Commands (COMP-CLI), Prompt Templates (COMP-PROMPTS) |

The CLI layer is the primary user-facing entry point. It orchestrates extraction, generation, benchmarking, and metrics display workflows by delegating to lower layers.

### Layer 1: MCP Server Layer (LAYER-MCP)

| Property | Value |
|----------|-------|
| **Order** | 1 (top — user-facing) |
| **Technology** | FastMCP, mcp-protocol |
| **Directory** | `src/opencode_arch/mcp/` |
| **Components** | MCP Server (COMP-MCP) |

The MCP Server layer exposes architecture tools to LLM agents via the Model Context Protocol. It operates at the same tier as the CLI — both are entry points, serving different consumers (humans vs. agents).

### Layer 2: Learning Layer (LAYER-LEARNING)

| Property | Value |
|----------|-------|
| **Order** | 2 (middle) |
| **Technology** | dataclasses, regex |
| **Directory** | `src/opencode_arch/learning/` |
| **Components** | Learning Loop (COMP-LEARNING) |

The Learning layer sits between the user-facing entry points and the infrastructure layers. It analyzes telemetry data to derive patterns and improve extraction strategies over time.

### Layer 3: Runner Layer (LAYER-RUNNER)

| Property | Value |
|----------|-------|
| **Order** | 3 (bottom — infrastructure) |
| **Technology** | subprocess, Protocol |
| **Directory** | `src/opencode_arch/runner/` |
| **Components** | OpenCode Runner (COMP-RUNNER) |

The Runner layer provides the execution backend for delegating prompts to the frontier model via subprocess. It implements the `RunnerBackend` protocol for pluggable model backends.

### Layer 3: Telemetry Layer (LAYER-TELEMETRY)

| Property | Value |
|----------|-------|
| **Order** | 3 (bottom — infrastructure) |
| **Technology** | SQLite |
| **Directory** | `src/opencode_arch/telemetry/` |
| **Components** | Telemetry Store (COMP-TELEMETRY) |

The Telemetry layer persists invocation metrics to a local SQLite database. It serves as a shared infrastructure dependency consumed by both the CLI and Learning layers.

## Layer Interaction Map

### Dependency Graph

```
┌─────────────────────────────────────────────────────┐
│  ORDER 1 — User-Facing Entry Points                 │
│                                                     │
│  ┌───────────────┐         ┌───────────────┐       │
│  │  CLI Commands │         │  MCP Server   │       │
│  │  (COMP-CLI)   │         │  (COMP-MCP)   │       │
│  └──┬──┬──┬──┬───┘         └───────┬───────┘       │
│     │  │  │  │                     │                │
├─────┼──┼──┼──┼─────────────────────┼────────────────┤
│  ORDER 2 — Business Logic          │                │
│     │  │  │  │                     │                │
│     │  │  │  └──► ┌────────────┐   │                │
│     │  │  │       │  Learning  │   │                │
│     │  │  │       │   Loop     │   │                │
│     │  │  │       └─────┬──────┘   │                │
│     │  │  │             │          │                │
├─────┼──┼──┼─────────────┼──────────┼────────────────┤
│  ORDER 3 — Infrastructure          │                │
│     │  │  │             │          │                │
│     │  │  └─► ┌─────────▼──────┐   │                │
│     │  │      │  Telemetry     │   │                │
│     │  │      │  Store         │   │                │
│     │  │      └────────────────┘   │                │
│     │  │                           │                │
│     │  └────► ┌────────────────┐   │                │
│     │         │  OpenCode      │   │                │
│     │         │  Runner        │   │                │
│     │         └────────────────┘   │                │
│     │                              │                │
│     └──────── ┌────────────────┐   │                │
│               │  Prompt        │   ▼                │
│               │  Templates     │  [Architecture     │
│               └────────────────┘   Model API]       │
│                                    (external)       │
└─────────────────────────────────────────────────────┘
```

### Dependency Summary

| Source | Target | Relationship | Cross-Layer |
|--------|--------|-------------|-------------|
| CLI Commands (order 1) | OpenCode Runner (order 3) | depends-on | 1 → 3 |
| CLI Commands (order 1) | Telemetry Store (order 3) | depends-on | 1 → 3 |
| CLI Commands (order 1) | Learning Loop (order 2) | depends-on | 1 → 2 |
| CLI Commands (order 1) | Prompt Templates (order 1) | depends-on | 1 → 1 (same layer) |
| MCP Server (order 1) | Architecture Model API | consumes | external interface |
| Learning Loop (order 2) | Telemetry Store (order 3) | depends-on | 2 → 3 |

### External Interfaces

The MCP Server consumes the **Architecture Model API** (IF-ARCH-MODEL), which is an external interface provided by the `architecture-model-standard` package. This is not an internal layer dependency but an external library consumption.

## Capability Realization

| Capability | Realized By | Layer |
|------------|-------------|-------|
| CAP-EXTRACT | CLI Commands | CLI (order 1) |
| CAP-GENERATE | CLI Commands | CLI (order 1) |
| CAP-DOCS | CLI Commands | CLI (order 1) |
| CAP-REGEN | CLI Commands | CLI (order 1) |
| CAP-MCP | MCP Server | MCP (order 1) |
| CAP-LEARN | Learning Loop | Learning (order 2) |
| CAP-TELEMETRY | Telemetry Store | Telemetry (order 3) |

## Constraints

| Constraint | Applied To | Layer |
|------------|-----------|-------|
| CON-TOKENS (token budget limits) | MCP Server | MCP (order 1) |
| CON-NO-HALLUCINATION (grounded output) | CLI Commands | CLI (order 1) |
| CON-TIMEOUT (execution time limits) | OpenCode Runner | Runner (order 3) |

## Layer Ordering Compliance

All dependencies flow in the correct direction (from lower order numbers to higher order numbers, i.e., from user-facing layers toward infrastructure):

- **Order 1 → Order 2**: CLI depends on Learning Loop — valid downward dependency.
- **Order 1 → Order 3**: CLI depends on Runner and Telemetry — valid downward dependency (skips order 2, which is acceptable in relaxed layering).
- **Order 2 → Order 3**: Learning depends on Telemetry — valid downward dependency.
- **Order 1 → Order 1**: CLI depends on Prompt Templates — valid same-layer dependency.

**No layer ordering violations detected.** The architecture follows a relaxed layered style where layers may skip intermediate layers when accessing infrastructure. No upward dependencies (higher order → lower order) exist.
