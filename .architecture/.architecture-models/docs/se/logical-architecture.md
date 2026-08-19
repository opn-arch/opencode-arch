---
document: Logical Architecture
system: opencode-arch
system_id: SYS-unknown
generated_at: 2026-08-19T16:58:20Z
generator_version: 0.3.0
model_hash: f2b902537f3a
edition: 4
---

# Logical Architecture: opencode-arch

## Layer Structure

*No layers defined.*

## Component Allocation

### unassigned

| Component | Kind | Files | Responsibilities |
|-----------|------|-------|------------------|
| Extraction Tools (COMP-1) | service | 5 files | — |
| Artifacts (COMP-2) | service | 4 files | — |
| CLI Commands (COMP-3) | service | 13 files | — |
| Requirements (COMP-4) | service | 5 files | — |
| Resolution (COMP-5) | service | 6 files | — |
| Context Tools (COMP-6) | service | 3 files | — |
| Model Management Tools (COMP-7) | service | 4 files | — |
| Documentation Tools (COMP-8) | service | 3 files | — |
| Quality Gate Tools (COMP-9) | service | 4 files | — |
| Requirements Tools (COMP-10) | service | 3 files | — |
| Live Analysis Tools (COMP-11) | service | 5 files | — |
| Runner (COMP-12) | service | 2 files | — |
| Telemetry (COMP-13) | service | 3 files | — |
| Learning (COMP-14) | service | 6 files | — |
| MCP Server (COMP-15) | service | 3 files | — |

## Inter-Component Interfaces

| Interface | Type | Protocol | Provider | Consumer |
|-----------|------|----------|----------|----------|
| run_benchmark CLI | internal | — | — | — |
| benchmark_economy CLI | internal | — | — | — |
| main CLI | internal | — | — | — |
| COMP-3-1 Library API | internal | — | — | — |
| COMP-3-2 Library API | internal | — | — | — |
| COMP-3-3 Library API | internal | — | — | — |
| COMP-3-4 Library API | internal | — | — | — |
| COMP-3-5 Library API | internal | — | — | — |
| COMP-3-6 Library API | internal | — | — | — |
| COMP-3-7 Library API | internal | — | — | — |
| COMP-3-8 Library API | internal | — | — | — |
| COMP-3-12 Library API | internal | — | — | — |
| COMP-3-13 Library API | internal | — | — | — |
| Extraction Tools API | internal | — | — | — |
| Requirements API | internal | — | — | — |
| Resolution API | internal | — | — | — |
| Context Tools API | internal | — | — | — |
| Model Management Tools API | internal | — | — | — |
| Documentation Tools API | internal | — | — | — |
| Quality Gate Tools API | internal | — | — | — |
| Requirements Tools API | internal | — | — | — |
| Live Analysis Tools API | internal | — | — | — |
| Runner API | internal | — | — | — |
| Telemetry API | internal | — | — | — |
| Learning API | internal | — | — | — |
| MCP Server API | internal | — | — | — |

## Dependency Graph

*No dependency relationships defined.*
