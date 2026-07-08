---
artifact_id: dependency-graph
generated_at: 2026-07-08T18:50:16.718778+00:00
generator: opencode-arch-docs
---
# Dependency Graph — opencode-arch

## Overview

This document describes the direct dependencies between components in the opencode-arch system, identifies coupling hotspots, and suggests structural improvements.

## Direct Dependencies

### Grouped by Source Component

#### COMP-CLI (CLI Commands)

| Target | Relationship |
|--------|-------------|
| COMP-RUNNER (OpenCode Runner) | depends-on |
| COMP-TELEMETRY (Telemetry Store) | depends-on |
| COMP-LEARNING (Learning Loop) | depends-on |
| COMP-PROMPTS (Prompt Templates) | depends-on |

#### COMP-LEARNING (Learning Loop)

| Target | Relationship |
|--------|-------------|
| COMP-TELEMETRY (Telemetry Store) | depends-on |

#### COMP-MCP (MCP Server)

| Target | Relationship |
|--------|-------------|
| IF-ARCH-MODEL (Architecture Model API) | consumes |

## Capability Realization

| Component | Capabilities Realized |
|-----------|----------------------|
| COMP-CLI | CAP-EXTRACT, CAP-GENERATE, CAP-DOCS, CAP-REGEN |
| COMP-MCP | CAP-MCP |
| COMP-LEARNING | CAP-LEARN |
| COMP-TELEMETRY | CAP-TELEMETRY |

## Constraints

| Constraint | Applied To |
|-----------|-----------|
| CON-TOKENS (Token budget limits) | COMP-MCP |
| CON-NO-HALLUCINATION (No hallucinated output) | COMP-CLI |
| CON-TIMEOUT (Execution timeout) | COMP-RUNNER |

## Dependency Analysis

### Coupling Metrics

| Component | Outgoing Dependencies | Incoming Dependencies | Total Coupling |
|-----------|----------------------|----------------------|----------------|
| COMP-CLI | 4 | 0 | 4 |
| COMP-TELEMETRY | 0 | 2 | 2 |
| COMP-LEARNING | 1 | 1 | 2 |
| COMP-RUNNER | 0 | 1 | 1 |
| COMP-PROMPTS | 0 | 1 | 1 |
| COMP-MCP | 1 (consumes) | 0 | 1 |

### Highly-Coupled Components

**COMP-CLI** is the highest-coupled component with 4 outgoing dependencies. It acts as the orchestration layer, depending on Runner, Telemetry, Learning, and Prompts to realize its four capabilities (extract, generate, docs, regen).

**COMP-TELEMETRY** is the most depended-upon component with 2 incoming dependencies (from CLI and Learning). It serves as a shared data sink.

### Circular Dependency Analysis

No circular dependencies exist in the current graph. The dependency flow is strictly acyclic:

```
COMP-CLI → COMP-LEARNING → COMP-TELEMETRY
COMP-CLI → COMP-TELEMETRY
COMP-CLI → COMP-RUNNER
COMP-CLI → COMP-PROMPTS
COMP-MCP ..> IF-ARCH-MODEL
```

The graph forms a DAG (directed acyclic graph) with COMP-CLI at the top and COMP-TELEMETRY, COMP-RUNNER, COMP-PROMPTS as leaf nodes.

### Observations

1. **COMP-CLI is a God Component risk** — It depends on 4 other components and realizes 4 capabilities. This high fan-out means changes to any dependency may require CLI changes.

2. **COMP-MCP is fully decoupled from COMP-CLI** — The MCP server consumes only the external Architecture Model API interface. These two subsystems share no internal dependencies.

3. **COMP-TELEMETRY is a stable dependency** — It has zero outgoing dependencies, making it a safe foundation for others to depend on.

### Suggested Improvements

1. **Reduce CLI fan-out** — Consider introducing a mediator or orchestration layer between COMP-CLI and its dependencies. Each CLI command could be a thin wrapper that delegates to a use-case object, rather than directly coupling to Runner, Telemetry, Learning, and Prompts.

2. **Abstract COMP-TELEMETRY behind an interface** — Since two components depend on Telemetry, introducing an interface (IF-TELEMETRY) would allow swapping implementations without affecting dependents.

3. **Consider unifying the CLI and MCP paths** — Currently COMP-CLI and COMP-MCP are isolated subgraphs. If they share behavioral logic in the future, a shared domain layer would prevent duplication without introducing coupling between them.
