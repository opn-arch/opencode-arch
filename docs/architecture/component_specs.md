# Component: CLI Commands (COMP-CLI)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/cli/main.py` | — | — |
| `src/opencode_arch/cli/extract.py` | — | — |
| `src/opencode_arch/cli/generate.py` | — | — |
| `src/opencode_arch/cli/bench.py` | — | — |
| `src/opencode_arch/cli/regen_loop.py` | — | — |
| `src/opencode_arch/cli/docs.py` | — | — |
| `src/opencode_arch/cli/docs_validator.py` | — | — |
| `src/opencode_arch/cli/metrics.py` | — | — |
| `src/opencode_arch/cli/gap_analyzer.py` | — | — |

## Responsibilities

- Parse CLI arguments
- Orchestrate extraction, generation, regen-loop, docs workflows
- Display results to user

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| COMP-RUNNER (OpenCode Runner) | depends-on | CLI uses runner to invoke LLM |
| COMP-TELEMETRY (Telemetry Store) | depends-on | CLI records metrics after operations |
| COMP-LEARNING (Learning Loop) | depends-on | Regen-loop uses learning for adaptation |
| COMP-PROMPTS (Prompt Templates) | depends-on | CLI uses prompt templates |
| CAP-EXTRACT | realizes | extract command realizes extraction capability |
| CAP-GENERATE | realizes | generate command realizes generation capability |
| CAP-DOCS | realizes | docs command realizes documentation capability |
| CAP-REGEN | realizes | regen-loop realizes subsystem regeneration |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| CON-NO-HALLUCINATION | constrained-by | Docs generator must only use grounded data |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: MCP Server (COMP-MCP)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/mcp/__main__.py` | — | — |
| `src/opencode_arch/mcp/server.py` | — | — |
| `src/opencode_arch/mcp/tools/scan.py` | — | — |
| `src/opencode_arch/mcp/tools/slice.py` | — | — |
| `src/opencode_arch/mcp/tools/validate.py` | — | — |
| `src/opencode_arch/mcp/tools/extract.py` | — | — |
| `src/opencode_arch/mcp/tools/generate.py` | — | — |

## Responsibilities

- Expose architecture tools via MCP protocol
- Compress context within token budget
- Bridge between LLM agent and architecture-model-standard

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| IF-ARCH-MODEL | consumes | MCP tools call architecture-model-standard APIs |
| CAP-MCP | realizes | MCP server realizes tool serving |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| CON-TOKENS | constrained-by | MCP tools must respect token budget |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: OpenCode Runner (COMP-RUNNER)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/runner/base.py` | — | — |
| `src/opencode_arch/runner/opencode.py` | — | — |

## Responsibilities

- Invoke opencode run as subprocess
- Handle timeouts and errors
- Return structured RunResult

## Relationships

### Dependencies (outgoing)

None

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-CLI (CLI Commands) | depends-on | CLI uses runner to invoke LLM |
| CON-TIMEOUT | constrained-by | Runner enforces timeout on subprocess |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Learning Loop (COMP-LEARNING)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/learning/classifier.py` | — | — |
| `src/opencode_arch/learning/adapter.py` | — | — |
| `src/opencode_arch/learning/assessor.py` | — | — |
| `src/opencode_arch/learning/lessons.py` | — | — |
| `src/opencode_arch/learning/maintainer.py` | — | — |
| `src/opencode_arch/learning/patterns.py` | — | — |

## Responsibilities

- Classify test failure patterns
- Adapt prompts based on patterns
- Generate report cards with grades
- Extract and store lessons
- Detect documentation drift

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| COMP-TELEMETRY (Telemetry Store) | depends-on | Learning stores lessons and patterns |
| CAP-LEARN | realizes | Learning module realizes learning loop |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-CLI (CLI Commands) | depends-on | Regen-loop uses learning for adaptation |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Telemetry Store (COMP-TELEMETRY)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/telemetry/store.py` | — | — |
| `src/opencode_arch/telemetry/recorder.py` | — | — |

## Responsibilities

- Persist tool invocation metrics
- Store regen outcomes and learning data
- Provide query interface for metrics display

## Relationships

### Dependencies (outgoing)

| Target | Type | Description |
|--------|------|-------------|
| CAP-TELEMETRY | realizes | Telemetry store realizes metrics tracking |

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-CLI (CLI Commands) | depends-on | CLI records metrics after operations |
| COMP-LEARNING (Learning Loop) | depends-on | Learning stores lessons and patterns |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%


---

# Component: Prompt Templates (COMP-PROMPTS)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/prompts/regen.py` | — | — |
| `src/opencode_arch/prompts/extract.py` | — | — |

## Responsibilities

- Define LLM prompt templates
- Structure system/user prompts for extraction and regen

## Relationships

### Dependencies (outgoing)

None

### Dependents (incoming)

| Source | Type | Description |
|--------|------|-------------|
| COMP-CLI (CLI Commands) | depends-on | CLI uses prompt templates |

## Behaviors Realized

None

## Patterns

None

## Confidence

0%
