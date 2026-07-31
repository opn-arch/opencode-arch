# API Detail — CAP-MCP: MCP Tool Serving

## Overview

| Field | Value |
|-------|-------|
| ID | CAP-MCP |
| F-Block | F4 (Agent Interface) |
| Priority | High |
| Realized by | COMP-MCP (`mcp/server.py`, `mcp/tools/`) |
| Actor | LLM Agent (ACT-AGENT) |
| Constraint | CON-TOKENS (4000 token budget) |

---

## MCP Server — `opencode_arch.mcp.server`

FastMCP server exposing 5 tools via stdio MCP protocol. Run with: `python -m opencode_arch.mcp`

---

### `architect_scan(repo_path: str) -> dict`

Scans a repository to generate its reality manifest via AST analysis.

**Delegates to:** `mcp/tools/scan.py::scan_repository()`

**Returns:** Manifest dict with modules, functions, classes, imports, metrics.

**Use case:** Agent calls this first to understand what's in a repo before slicing.

---

### `architect_slice(repo_path: str, focus: str = "all", budget: int = 4000, detail: str = "standard") -> str`

The **core token-arbitrage function**. Compresses an entire repository into a dense context string within the token budget.

**Parameters:**

| Param | Default | Options |
|-------|---------|---------|
| `repo_path` | — | Absolute path to repository |
| `focus` | `"all"` | `"all"`, F-block ID (`"F1"`), layer name, artifact name (`"icd"`) |
| `budget` | 4000 | Maximum token budget |
| `detail` | `"standard"` | `"minimal"`, `"standard"`, `"full"` |

**Delegates to:** `mcp/tools/slice.py::slice_context()` which calls `format_model_context()` / `format_fblock_context()` / `format_artifact_context()`

**Returns:** Formatted text string suitable for LLM system prompt injection. ~25:1 compression vs full artifact markdown.

---

### `architect_validate(model_yaml: str) -> dict`

Validates an architecture model YAML string for structural correctness.

**Checks performed:** ID uniqueness, referential integrity, orphan detection, capability realization, meta completeness, regen readiness.

**Returns:**

| Key | Type | Description |
|-----|------|-------------|
| `score` | `int` | 0-100 validation score |
| `is_valid` | `bool` | True if 0 errors |
| `issues` | `list[dict]` | Each with severity, code, message |
| `entity_count` | `int` | Total entities in model |
| `relationship_count` | `int` | Total relationships |

---

### `architect_extract(repo_path: str, model_yaml: str, context_tokens: int = 0) -> dict`

Stores a validated architecture extraction. Called AFTER the agent produces a YAML model.

**Algorithm:**

1. Parse YAML string into `ArchitectureModel` via `_parse_raw()`
2. Validate model (must score >= threshold)
3. Write to `<repo_path>/.architecture-model.yaml`
4. Record telemetry

**Returns:**

| Key | Type | Description |
|-----|------|-------------|
| `stored` | `bool` | Whether model was saved |
| `score` | `int` | Validation score |
| `path` | `str` | Where model was written |
| `issues` | `list[str]` | Validation issues |

---

### `architect_generate(repo_path: str, test_command: str = "") -> dict`

Runs tests on generated code to verify quality.

**Returns:**

| Key | Type | Description |
|-----|------|-------------|
| `pass_rate` | `float` | 0.0-1.0 |
| `passed` | `int` | Passing tests |
| `failed` | `int` | Failing tests |
| `total` | `int` | Total tests |
| `output` | `str` | Test output (truncated) |

---

## Context Formatter — `opencode_arch.context.formatter`

The compression engine behind `architect_slice`.

### `format_model_context(model, max_tokens=4000, detail_level="standard") -> str`

Formats the full model as compact LLM context within a token budget (1 token ≈ 4 chars).

**Detail levels:**

| Level | Includes |
|-------|----------|
| `minimal` | Header + relationships only |
| `standard` | + capabilities, actors, compact behaviors/interfaces/layers |
| `full` | + full behaviors, interfaces, layers, components, constraints |

Truncates with `[... truncated]` if over budget.

### `format_fblock_context(model, f_block, max_tokens=2000) -> str`

Slices by F-block then formats at `full` detail. For focused subsystem work.

### `format_artifact_context(model, artifact_name, max_tokens=3000) -> str`

Slices for a specific artifact then formats at appropriate detail level:
- functional-architecture, logical-architecture, use-cases, icd → `full`
- requirements-analysis → `standard`
- readme → `minimal`

### `query_model(model, question) -> str`

Answers structural questions about the model (entity counts, relationship types, etc.).

### `impact_analysis(model, entity_id, depth) -> str`

BFS traversal from entity_id, returns formatted impact chain.

---

## Behavioral View: BEH-MCP-SCAN

**Trigger:** Agent calls `architect_scan` tool

```
LLM Agent ──► MCP Server (architect_scan)
                 │
                 ├─► generate_manifest(repo_path)
                 │
LLM Agent ◄── manifest dict
```

Typical agent workflow:
1. `architect_scan` → understand repo structure
2. `architect_slice` → get compressed context for specific focus
3. (agent generates model YAML)
4. `architect_validate` → check quality
5. `architect_extract` → persist if valid
