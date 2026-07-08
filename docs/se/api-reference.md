---
artifact_id: api-reference
generated_at: 2026-07-08T18:42:40.757796+00:00
generator: opencode-arch-docs
---
# API Reference — opencode-arch

## Overview

This document describes the interfaces exposed by the `opencode-arch` package. The system provides five interface boundaries: a CLI for developer interaction, an MCP tool protocol for LLM agents, a pluggable runner backend, a telemetry persistence layer, and an internal dependency on the `architecture-model-standard` library.

---

## IF-CLI: CLI Interface

| Property | Value |
|----------|-------|
| **ID** | IF-CLI |
| **Type** | Internal |
| **Protocol** | argparse |
| **Provider** | COMP-CLI |
| **Consumer** | ACT-DEV |
| **Endpoints** | 6 |
| **Data Format** | Command-line arguments (positional + optional flags) |

### Entry Point

```
opencode-arch <command> [options]
```

### Endpoints

#### 1. `extract`

```
opencode-arch extract <repo_path> [--budget INT] [--focus STR] [--target-score INT] [--model STR] [--timeout INT]
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `repo_path` | str | yes | — | Path to target repository |
| `--budget` | int | no | 4000 | Token budget for context |
| `--focus` | str | no | `"all"` | Focus scope |
| `--target-score` | int | no | 80 | Minimum validation score |
| `--model` | str | no | None | Model override |
| `--timeout` | int | no | 600 | Timeout in seconds |

#### 2. `generate`

```
opencode-arch generate <repo_path> [--max-iter INT] [--test-command STR] [--model STR] [--timeout INT]
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `repo_path` | str | yes | — | Path to target repository |
| `--max-iter` | int | no | 3 | Maximum iteration attempts |
| `--test-command` | str | no | None | Custom test command |
| `--model` | str | no | None | Model override |
| `--timeout` | int | no | 600 | Timeout in seconds |

#### 3. `bench`

```
opencode-arch bench <repos...> [--output STR] [--model STR]
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `repos` | str (nargs=+) | yes | — | One or more repository paths |
| `--output` | str | no | None | Output file for metrics JSON |
| `--model` | str | no | None | Model override |

#### 4. `metrics`

```
opencode-arch metrics [--tool STR] [--last INT] [--learning-curve] [--drift]
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `--tool` | str | no | None | Filter by tool name |
| `--last` | int | no | 10 | Number of recent records |
| `--learning-curve` | flag | no | False | Show learning curve data |
| `--drift` | flag | no | False | Show drift flags |

#### 5. `report`

```
opencode-arch report [--repo STR] [--last INT]
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `--repo` | str | no | None | Filter by repository |
| `--last` | int | no | 5 | Number of recent reports |

#### 6. `regen-loop`

```
opencode-arch regen-loop --repo STR [--max-iterations INT] [--target FLOAT] [--subsystem STR] [--blind] [--model STR] [--timeout INT]
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `--repo` | str | yes | — | Target repository path |
| `--max-iterations` | int | no | 5 | Maximum regeneration iterations |
| `--target` | float | no | 0.5 | Target pass rate |
| `--subsystem` | str | no | None | Specific subsystem to target |
| `--blind` | flag | no | False | Run in blind mode |
| `--model` | str | no | None | Model override |
| `--timeout` | int | no | 600 | Timeout in seconds |

---

## IF-MCP: MCP Tool Protocol

| Property | Value |
|----------|-------|
| **ID** | IF-MCP |
| **Type** | External |
| **Protocol** | MCP stdio |
| **Provider** | COMP-MCP |
| **Consumer** | ACT-AGENT |
| **Endpoints** | 5 |
| **Data Format** | JSON (MCP tool call/response) |

### Server Configuration

- **Server name:** `opencode-arch`
- **Transport:** stdio
- **Instructions:** "Architecture context compression, validation, and code quality tools"

### Endpoints

#### 1. `architect_scan`

Generates a reality manifest via AST scanning of the repository.

```
architect_scan(repo_path: str) -> dict
```

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_path` | str | yes | Absolute path to the repository root |

**Response Schema:**

```json
{
  "generated_at": "ISO 8601 timestamp",
  "project_root": "/absolute/path",
  "metrics": { ... },
  "functional_blocks": [ ... ],
  "modules": [ ... ],
  "interfaces": [ ... ]
}
```

**Error Response:**

```json
{
  "error": "Description of what went wrong"
}
```

#### 2. `architect_slice`

Compresses repository structure into a dense context string within the token budget.

```
architect_slice(repo_path: str, focus: str = "all", budget: int = 4000, detail: str = "standard") -> str
```

**Request Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `repo_path` | str | yes | — | Absolute path to the repository root |
| `focus` | str | no | `"all"` | Focus scope: `"all"`, F-block ID (`"F1"`), layer name, or artifact name (`"icd"`) |
| `budget` | int | no | 4000 | Maximum token budget (1 token ≈ 4 chars) |
| `detail` | str | no | `"standard"` | Detail level: `"minimal"`, `"standard"`, or `"full"` |

**Response:** Plain text string containing compressed context. If `.architecture-model.yaml` exists in the repo, uses the rich model+slicer+formatter path; otherwise falls back to manifest-based compact YAML.

#### 3. `architect_validate`

Validates an architecture model YAML for structural correctness.

```
architect_validate(model_yaml: str) -> dict
```

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model_yaml` | str | yes | YAML architecture model string to validate |

**Response Schema:**

```json
{
  "score": 85,
  "issues": ["Issue description 1", "Issue description 2"],
  "entity_count": 12,
  "relationship_count": 8,
  "is_valid": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `score` | int (0-100) | Structural correctness score |
| `issues` | list[str] | Validation issues found |
| `entity_count` | int | Number of entities in model |
| `relationship_count` | int | Number of relationships in model |
| `is_valid` | bool | Whether model passes validation |

#### 4. `architect_extract`

Stores a validated architecture extraction to disk and records telemetry.

```
architect_extract(repo_path: str, model_yaml: str, context_tokens: int = 0) -> dict
```

**Request Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `repo_path` | str | yes | — | Path to the repository root |
| `model_yaml` | str | yes | — | YAML architecture model produced by the agent |
| `context_tokens` | int | no | 0 | Tokens of context used (for telemetry) |

**Response Schema:**

```json
{
  "stored": true,
  "score": 85,
  "issues": [],
  "path": "/path/to/repo/.architecture-model.yaml",
  "telemetry_recorded": true
}
```

**Error Response:**

```json
{
  "stored": false,
  "error": "Description of what went wrong",
  "score": 0
}
```

#### 5. `architect_generate`

Runs the repository's test suite against generated code.

```
architect_generate(repo_path: str, test_command: str = "") -> dict
```

**Request Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `repo_path` | str | yes | — | Path to the repository with generated code |
| `test_command` | str | no | `""` | Custom test command; defaults to pytest |

**Response Schema:**

```json
{
  "passed": true,
  "pass_rate": 0.95,
  "total_tests": 20,
  "passed_tests": 19,
  "failures": ["test_something: AssertionError"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `passed` | bool | Whether all tests passed |
| `pass_rate` | float (0.0-1.0) | Ratio of passed to total tests |
| `total_tests` | int | Total number of tests discovered |
| `passed_tests` | int | Number of tests that passed |
| `failures` | list[str] | Descriptions of failed tests |

---

## IF-RUNNER: Runner Backend Protocol

| Property | Value |
|----------|-------|
| **ID** | IF-RUNNER |
| **Type** | Internal |
| **Protocol** | subprocess |
| **Provider** | COMP-RUNNER |
| **Consumer** | COMP-CLI |
| **Endpoints** | 1 |
| **Data Format** | Python Protocol (duck typing) |

### Protocol Definition

```python
class RunnerBackend(Protocol):
    async def run(self, prompt: str, repo_path: str) -> RunResult
```

### Endpoint

#### `run`

Executes an agent with a prompt in the context of a repository.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `prompt` | str | The full prompt to send to the agent |
| `repo_path` | str | Absolute path to the target repository |

**Return Type: `RunResult`**

```python
@dataclass
class RunResult:
    output: str      # The agent's text output
    exit_code: int   # Process exit code (0 = success)
    success: bool    # Whether the run succeeded
```

### Default Implementation: `OpencodeRunner`

Invokes `opencode run` as a subprocess.

**Constructor:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `timeout` | int | 600 | Maximum seconds before timeout |
| `model` | str \| None | None | Model override flag |

**Subprocess invocation:**

```
opencode run [--model MODEL]
```

- Prompt passed via stdin (avoids ARG_MAX limits)
- Working directory set to `repo_path` via `cwd`
- ANSI escape codes stripped from stdout

---

## IF-TELEMETRY: Telemetry Store Interface

| Property | Value |
|----------|-------|
| **ID** | IF-TELEMETRY |
| **Type** | Internal |
| **Protocol** | SQLite |
| **Provider** | COMP-TELEMETRY |
| **Consumer** | COMP-CLI |
| **Endpoints** | 3 |
| **Data Format** | SQLite rows / Python dicts |

### Database Location

Default: `~/.opencode-arch/telemetry.db`

### Endpoints

#### 1. `record`

Records a tool invocation.

```python
def record(self, tool: str, repo: str = "", context_tokens: int = 0,
           output_quality: int = 0, iterations: int = 1, metadata: str = "")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tool` | str | — | Tool name (e.g. `"extract"`, `"validate"`) |
| `repo` | str | `""` | Target repository name |
| `context_tokens` | int | 0 | Tokens of context consumed |
| `output_quality` | int | 0 | Validation score (0-100) |
| `iterations` | int | 1 | Number of attempts |
| `metadata` | str | `""` | Additional JSON metadata |

**Storage schema (`invocations` table):**

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-increment primary key |
| `timestamp` | REAL | Unix timestamp |
| `tool` | TEXT | Tool identifier |
| `repo` | TEXT | Repository name |
| `context_tokens` | INTEGER | Tokens used |
| `output_quality` | INTEGER | Score 0-100 |
| `iterations` | INTEGER | Attempt count |
| `metadata` | TEXT | JSON string |

#### 2. `query`

Retrieves recorded invocations with optional filtering.

```python
def query(self, tool: str | None = None, limit: int = 100) -> list[dict[str, Any]]
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tool` | str \| None | None | Filter by tool name |
| `limit` | int | 100 | Maximum records to return |

**Returns:** List of dicts matching the `invocations` table schema, ordered by most recent first.

#### 3. `averages`

Computes average metrics for a specific tool.

```python
def averages(self, tool: str) -> dict[str, float]
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `tool` | str | Tool name to compute averages for |

**Response Schema:**

```json
{
  "avg_context_tokens": 3200.0,
  "avg_output_quality": 78.5,
  "avg_iterations": 1.3
}
```

### Async Wrapper

```python
async def record_invocation(store: TelemetryStore, tool: str, repo: str = "",
                            context_tokens: int = 0, output_quality: int = 0,
                            iterations: int = 1, metadata: str = "")
```

Provides an async entry point that delegates to `store.record()`. Designed to be called from async tool handlers without blocking.

---

## IF-ARCH-MODEL: Architecture Model API

| Property | Value |
|----------|-------|
| **ID** | IF-ARCH-MODEL |
| **Type** | Internal |
| **Protocol** | Python import |
| **Provider** | ACT-OPENCODE (architecture-model-standard package) |
| **Consumer** | COMP-CLI |
| **Endpoints** | 4 |
| **Data Format** | Python objects / YAML strings |

### Dependency

```
architecture-model-standard >= 0.3.0
```

### Endpoints

#### 1. `generate_manifest()`

AST-scans a repository and produces a structured manifest.

**Consumed by:** `scan_repository()` in `src/opencode_arch/mcp/tools/scan.py`

**Returns:** Manifest dict with modules, functions, classes, imports, metrics, and functional blocks.

#### 2. `format_model_context()`

Formats an architecture model into a compressed context string for LLM consumption.

**Consumed by:** `slice_context()` in `src/opencode_arch/mcp/tools/slice.py`

**Used when:** `.architecture-model.yaml` exists (rich path).

#### 3. `validate_model()`

Validates a parsed architecture model for structural correctness. Checks: ID uniqueness, referential integrity, orphan detection, capability realization, meta completeness.

**Consumed by:** `validate_architecture()` in `src/opencode_arch/mcp/tools/validate.py`

**Returns:** Score (0-100), list of issues, entity/relationship counts.

#### 4. Slicer API

Subsets a model by focus area (F-block, layer, artifact) before formatting.

**Consumed by:** `_slice_from_model()` in `src/opencode_arch/mcp/tools/slice.py`

**Parameters:** Model object, focus identifier, budget constraint, detail level.

---

## Data Contracts

### Architecture Model YAML Schema

The canonical data contract between the agent and the storage layer:

```yaml
meta:
  project: string        # Project name
  schema_version: '1.3'  # Schema version

entities:
  components:
    - id: string         # Format: COMP-{N}
      name: string
      status: enum       # ACTIVE | PLANNED | DEPRECATED

  capabilities:
    - id: string         # Format: CAP-{ID}
      name: string
      status: enum       # ACTIVE | PLANNED | DEPRECATED

  layers:
    - id: string         # Format: LAYER-{N}
      name: string
      status: enum

  behaviors:
    - id: string
      name: string

  interfaces:
    - id: string
      name: string

  constraints:
    - id: string
      name: string

  actors:
    - id: string
      name: string

relationships:
  - from: string         # Entity ID reference
    to: string           # Entity ID reference
    type: enum           # realizes | uses | constrains | contains |
                         # triggers | depends_on | implements | exposes
```

### MCP Request/Response Contract

All MCP tools follow the standard MCP tool call protocol over stdio:

- **Request:** JSON-RPC with `tool_name` and `arguments` object
- **Response:** JSON-RPC with `content` (text or structured data)
- **Error:** Standard MCP error response with error code and message

### RunResult Contract

The data contract between runner backends and the CLI:

| Field | Type | Invariants |
|-------|------|------------|
| `output` | str | Raw text from agent; ANSI codes stripped |
| `exit_code` | int | 0 = success; -1 = internal error (timeout, not found) |
| `success` | bool | `True` iff `exit_code == 0` |

### Telemetry Record Contract

Each tool invocation produces exactly one `invocations` row:

| Field | Invariants |
|-------|------------|
| `timestamp` | Set at write time; monotonically increasing |
| `tool` | One of: `"scan"`, `"slice"`, `"validate"`, `"extract"`, `"generate"` |
| `repo` | Repository basename or empty string |
| `context_tokens` | Non-negative integer |
| `output_quality` | Integer 0-100 |
| `iterations` | Positive integer (minimum 1) |
