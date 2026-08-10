# Component: MCP Server (COMP-MCP)

**Status:** Status.ACTIVE
**Description:** FastMCP server with 20+ tool implementations (scan, extract, slice, check, etc.)

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/mcp/__init__.py` | — | — |
| `src/opencode_arch/mcp/__main__.py` | — | — |
| `src/opencode_arch/mcp/server.py` | — | — |
| `src/opencode_arch/mcp/quality.py` | — | — |
| `src/opencode_arch/mcp/tools/__init__.py` | — | — |
| `src/opencode_arch/mcp/tools/author.py` | — | — |
| `src/opencode_arch/mcp/tools/check.py` | — | — |
| `src/opencode_arch/mcp/tools/correct.py` | — | — |
| `src/opencode_arch/mcp/tools/decompose.py` | — | — |
| `src/opencode_arch/mcp/tools/docs.py` | — | — |
| `src/opencode_arch/mcp/tools/export.py` | — | — |
| `src/opencode_arch/mcp/tools/extract.py` | — | — |
| `src/opencode_arch/mcp/tools/feedback.py` | — | — |
| `src/opencode_arch/mcp/tools/gate.py` | — | — |
| `src/opencode_arch/mcp/tools/generate.py` | — | — |
| `src/opencode_arch/mcp/tools/group.py` | — | — |
| `src/opencode_arch/mcp/tools/ingest.py` | — | — |
| `src/opencode_arch/mcp/tools/llm_audit.py` | — | — |
| `src/opencode_arch/mcp/tools/regen_score.py` | — | — |
| `src/opencode_arch/mcp/tools/require.py` | — | — |
| `src/opencode_arch/mcp/tools/scan.py` | — | — |
| `src/opencode_arch/mcp/tools/slice.py` | — | — |
| `src/opencode_arch/mcp/tools/stats.py` | — | — |
| `src/opencode_arch/mcp/tools/trace_requirements.py` | — | — |
| `src/opencode_arch/mcp/tools/validate.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-MCP | realizes | — |
| COMP-CONTEXT (Context) | depends-on | — |
| COMP-ARTIFACTS (Artifacts) | depends-on | — |
| COMP-REGEN (Regen) | depends-on | — |
| COMP-TELEMETRY (Telemetry) | depends-on | — |
| COMP-REQUIREMENTS (Requirements) | depends-on | — |
| COMP-LLM (LLM) | depends-on | — |
| IF-MCP | exposes | — |
| IF-ARCH-STD | consumes | — |
| CON-TOKEN-BUDGET | constrained-by | — |
| CON-ARCH-STD-DEP | constrained-by | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-MCP | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Context (COMP-CONTEXT)

**Status:** Status.ACTIVE
**Description:** Context compression, token brokering, pipeline bridge to arch-std

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/context/__init__.py` | — | — |
| `src/opencode_arch/context/formatter.py` | — | — |
| `src/opencode_arch/context/pipeline_bridge.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-CONTEXT | realizes | — |
| COMP-LLM (LLM) | depends-on | — |
| IF-ARCH-STD | consumes | — |
| CON-TOKEN-BUDGET | constrained-by | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-DOMAIN | contains | — |
| COMP-MCP (MCP Server) | depends-on | — |
| COMP-CLI (CLI) | depends-on | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Artifacts (COMP-ARTIFACTS)

**Status:** Status.ACTIVE
**Description:** Artifact selection, context assembly, diagram generation, templates

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/artifacts/__init__.py` | — | — |
| `src/opencode_arch/artifacts/context.py` | — | — |
| `src/opencode_arch/artifacts/diagrams.py` | — | — |
| `src/opencode_arch/artifacts/selector.py` | — | — |
| `src/opencode_arch/artifacts/templates.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-ARTIFACTS | realizes | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-DOMAIN | contains | — |
| COMP-MCP (MCP Server) | depends-on | — |
| COMP-CLI (CLI) | depends-on | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Learning (COMP-LEARNING)

**Status:** Status.ACTIVE
**Description:** Pattern classifier, adaptive prompting, report cards, lessons, drift maintenance

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/learning/__init__.py` | — | — |
| `src/opencode_arch/learning/adapter.py` | — | — |
| `src/opencode_arch/learning/assessor.py` | — | — |
| `src/opencode_arch/learning/classifier.py` | — | — |
| `src/opencode_arch/learning/lessons.py` | — | — |
| `src/opencode_arch/learning/maintainer.py` | — | — |
| `src/opencode_arch/learning/patterns.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-LEARNING | realizes | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-DOMAIN | contains | — |
| COMP-CLI (CLI) | depends-on | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Regen (COMP-REGEN)

**Status:** Status.ACTIVE
**Description:** Spot-check probe, self-healing, regen loop orchestration

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/regen/__init__.py` | — | — |
| `src/opencode_arch/regen/spot_check.py` | — | — |
| `src/opencode_arch/regen/self_heal.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-SPOT-CHECK | realizes | — |
| COMP-LLM (LLM) | depends-on | — |
| BEH-SPOT | traces-to | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-DOMAIN | contains | — |
| COMP-MCP (MCP Server) | depends-on | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: CLI (COMP-CLI)

**Status:** Status.ACTIVE
**Description:** CLI commands: extract, bench, regen, docs, metrics, calibrate, confidence, launch

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/cli/__init__.py` | — | — |
| `src/opencode_arch/cli/main.py` | — | — |
| `src/opencode_arch/cli/bench.py` | — | — |
| `src/opencode_arch/cli/calibrate.py` | — | — |
| `src/opencode_arch/cli/confidence.py` | — | — |
| `src/opencode_arch/cli/docs.py` | — | — |
| `src/opencode_arch/cli/docs_validator.py` | — | — |
| `src/opencode_arch/cli/export_data.py` | — | — |
| `src/opencode_arch/cli/extract.py` | — | — |
| `src/opencode_arch/cli/gap_analyzer.py` | — | — |
| `src/opencode_arch/cli/generate.py` | — | — |
| `src/opencode_arch/cli/launch.py` | — | — |
| `src/opencode_arch/cli/metrics.py` | — | — |
| `src/opencode_arch/cli/prompts.py` | — | — |
| `src/opencode_arch/cli/regen_loop.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-REGEN | realizes | — |
| CAP-BENCH | realizes | — |
| COMP-CONTEXT (Context) | depends-on | — |
| COMP-LEARNING (Learning) | depends-on | — |
| COMP-LLM (LLM) | depends-on | — |
| COMP-ARTIFACTS (Artifacts) | depends-on | — |
| IF-CLI | exposes | — |
| BEH-EXTRACT | traces-to | — |
| BEH-REGEN | traces-to | — |
| CON-NO-SOURCE-IN-BLIND | constrained-by | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-CLI | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Requirements (COMP-REQUIREMENTS)

**Status:** Status.ACTIVE
**Description:** Requirement capture, matching, storage

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/requirements/__init__.py` | — | — |
| `src/opencode_arch/requirements/matcher.py` | — | — |
| `src/opencode_arch/requirements/store.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-REQUIREMENTS | realizes | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-DOMAIN | contains | — |
| COMP-MCP (MCP Server) | depends-on | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Agent (COMP-AGENT)

**Status:** Status.ACTIVE
**Description:** Uncertainty resolution — dispatches to LLM/search/user

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/agent/__init__.py` | — | — |
| `src/opencode_arch/agent/resolution.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-RESOLUTION | realizes | — |
| COMP-LLM (LLM) | depends-on | — |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-INFRA | contains | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: LLM (COMP-LLM)

**Status:** Status.ACTIVE
**Description:** LLM caching, prompt templates (audit, matching, requirements)

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/llm/__init__.py` | — | — |
| `src/opencode_arch/llm/cache.py` | — | — |
| `src/opencode_arch/llm/prompts/__init__.py` | — | — |
| `src/opencode_arch/llm/prompts/audit.py` | — | — |
| `src/opencode_arch/llm/prompts/matching.py` | — | — |
| `src/opencode_arch/llm/prompts/requirements.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

None

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-INFRA | contains | — |
| COMP-CLI (CLI) | depends-on | — |
| COMP-CONTEXT (Context) | depends-on | — |
| COMP-REGEN (Regen) | depends-on | — |
| COMP-AGENT (Agent) | depends-on | — |
| COMP-MCP (MCP Server) | depends-on | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Telemetry (COMP-TELEMETRY)

**Status:** Status.ACTIVE
**Description:** Session tracking, quality metrics, historical statistics

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/telemetry/__init__.py` | — | — |
| `src/opencode_arch/telemetry/session.py` | — | — |
| `src/opencode_arch/telemetry/store.py` | — | — |

## Responsibilities

—

## Relationships

### Dependencies (outgoing)

None

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| LYR-INFRA | contains | — |
| COMP-MCP (MCP Server) | depends-on | — |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%
