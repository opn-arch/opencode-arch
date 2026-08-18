# System Design: opencode-arch

## Architecture Overview

—
Schema version: 1.3

## Component Inventory

| ID | Name | Status | Files | Behaviors |
|----|------|--------|-------|-----------|
| COMP-1 | Extraction Tools | Status.ACTIVE | 5 | 0 |
| COMP-2 | Artifacts | Status.ACTIVE | 4 | 0 |
| COMP-3 | CLI Commands | Status.ACTIVE | 13 | 0 |
| COMP-4 | Requirements | Status.ACTIVE | 5 | 0 |
| COMP-5 | Resolution | Status.ACTIVE | 6 | 0 |
| COMP-6 | Context Tools | Status.ACTIVE | 3 | 0 |
| COMP-7 | Model Management Tools | Status.ACTIVE | 4 | 0 |
| COMP-8 | Documentation Tools | Status.ACTIVE | 3 | 0 |
| COMP-9 | Quality Gate Tools | Status.ACTIVE | 4 | 0 |
| COMP-10 | Requirements Tools | Status.ACTIVE | 3 | 0 |
| COMP-11 | Live Analysis Tools | Status.ACTIVE | 5 | 0 |
| COMP-12 | Runner | Status.ACTIVE | 2 | 0 |
| COMP-13 | Telemetry | Status.ACTIVE | 3 | 0 |
| COMP-14 | Learning | Status.ACTIVE | 6 | 0 |
| COMP-15 | MCP Server | Status.ACTIVE | 3 | 0 |

## Key Behaviors

- **CLI: Run Benchmark** (BEH-1)
- **CLI: Benchmark Economy** (BEH-2)
- **CLI: Main** (BEH-3)

## Relationship Summary

| Type | Count |
|------|-------|
| exposes | 3 |
| satisfies | 27 |
| uses | 30 |
