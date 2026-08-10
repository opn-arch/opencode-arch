# Integration Flows: opencode-arch

```mermaid
flowchart TD
  COMP-MCP[MCP Server] -->|depends-on| COMP-CONTEXT[Context]
  COMP-MCP[MCP Server] -->|depends-on| COMP-ARTIFACTS[Artifacts]
  COMP-MCP[MCP Server] -->|depends-on| COMP-REGEN[Regen]
  COMP-MCP[MCP Server] -->|depends-on| COMP-TELEMETRY[Telemetry]
  COMP-MCP[MCP Server] -->|depends-on| COMP-REQUIREMENTS[Requirements]
  COMP-CLI[CLI] -->|depends-on| COMP-CONTEXT[Context]
  COMP-CLI[CLI] -->|depends-on| COMP-LEARNING[Learning]
  COMP-CLI[CLI] -->|depends-on| COMP-LLM[LLM]
  COMP-CLI[CLI] -->|depends-on| COMP-ARTIFACTS[Artifacts]
  COMP-CONTEXT[Context] -->|depends-on| COMP-LLM[LLM]
  COMP-REGEN[Regen] -->|depends-on| COMP-LLM[LLM]
  COMP-AGENT[Agent] -->|depends-on| COMP-LLM[LLM]
  COMP-MCP[MCP Server] -->|depends-on| COMP-LLM[LLM]
```

## MCP Server → Context (depends-on)
—

**Source:** COMP-MCP (MCP Server)
**Target:** COMP-CONTEXT (Context)

## MCP Server → Artifacts (depends-on)
—

**Source:** COMP-MCP (MCP Server)
**Target:** COMP-ARTIFACTS (Artifacts)

## MCP Server → Regen (depends-on)
—

**Source:** COMP-MCP (MCP Server)
**Target:** COMP-REGEN (Regen)

## MCP Server → Telemetry (depends-on)
—

**Source:** COMP-MCP (MCP Server)
**Target:** COMP-TELEMETRY (Telemetry)

## MCP Server → Requirements (depends-on)
—

**Source:** COMP-MCP (MCP Server)
**Target:** COMP-REQUIREMENTS (Requirements)

## CLI → Context (depends-on)
—

**Source:** COMP-CLI (CLI)
**Target:** COMP-CONTEXT (Context)

## CLI → Learning (depends-on)
—

**Source:** COMP-CLI (CLI)
**Target:** COMP-LEARNING (Learning)

## CLI → LLM (depends-on)
—

**Source:** COMP-CLI (CLI)
**Target:** COMP-LLM (LLM)

## CLI → Artifacts (depends-on)
—

**Source:** COMP-CLI (CLI)
**Target:** COMP-ARTIFACTS (Artifacts)

## Context → LLM (depends-on)
—

**Source:** COMP-CONTEXT (Context)
**Target:** COMP-LLM (LLM)

## Regen → LLM (depends-on)
—

**Source:** COMP-REGEN (Regen)
**Target:** COMP-LLM (LLM)

## Agent → LLM (depends-on)
—

**Source:** COMP-AGENT (Agent)
**Target:** COMP-LLM (LLM)

## MCP Server → LLM (depends-on)
—

**Source:** COMP-MCP (MCP Server)
**Target:** COMP-LLM (LLM)
