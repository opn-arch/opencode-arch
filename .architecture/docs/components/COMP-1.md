# Component: Extraction Tools (COMP-1)

**Status:** Status.ACTIVE
**Description:** Source in src/opencode_arch/mcp/tools (5 files)

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/mcp/tools/scan.py` | — | — |
| `src/opencode_arch/mcp/tools/extract.py` | — | — |
| `src/opencode_arch/mcp/tools/group.py` | — | — |
| `src/opencode_arch/mcp/tools/ingest.py` | — | — |
| `src/opencode_arch/mcp/tools/pipeline.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| COMP-13 (Telemetry) | uses | Extraction Tools imports from Telemetry |
| COMP-15 (MCP Server) | uses | Extraction Tools imports from MCP Server |
| COMP-8 (Documentation Tools) | uses | Extraction Tools imports from Documentation Tools |
| REQ-Q15 | satisfies | — |
| REQ-Q16 | satisfies | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-15 (MCP Server) | uses | MCP Server imports from Extraction Tools |
| COMP-3 (CLI Commands) | uses | CLI Commands imports from Extraction Tools |

## Behaviors Realized

None

## Interface Dependencies

- **provides** `exposes_to_Cli` → COMP-3 (CLI Commands) [store_extraction]
- **requires** `uses_Resolution` → COMP-5 (Resolution) [estimate_regenerability, check_fidelity, with_quality, SessionAccumulator]
- **requires** `uses_Cli` → COMP-3 (CLI Commands) [drain_and_store]
- **requires** `uses_Requirements` → COMP-4 (Requirements) [hash_content, cached_llm_call, CachedResult, LLMCache]

## Patterns

None

## Confidence

45%
