# opencode-arch

**Architecture extraction and validation for Python codebases.**

Mechanically verify that your architecture model matches your code. Compress entire repositories into ~430 tokens for AI agents. Produce training data for LLM fine-tuning.

![PyPI](https://img.shields.io/pypi/v/opencode-arch)
![Python](https://img.shields.io/pypi/pyversions/opencode-arch)
![Tests](https://img.shields.io/badge/tests-278%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## Why

| Problem | Solution |
|---------|----------|
| Architecture docs drift from code | Mechanical representativeness scoring — know exactly when your model is wrong |
| AI agents burn tokens reading every file | Token arbitrage — full repo AST compressed to ~430 tokens of dense context |
| No structured architecture data for training | Produces (code, model, metrics) triples ready for fine-tuning |
| Manual component boundary decisions | Auto-groups modules by import affinity, name prefix, and subdirectory |

## Features

- **Representativeness Scoring** — File coverage, relationship accuracy, boundary coherence, behavioral coverage. Four mechanical sub-scores that tell you if your model is accurate.
- **Token Arbitrage** — Compress a full repository's AST into a dense context string within any token budget. Agents reason about the whole codebase without reading every file.
- **Living Documentation** — Components, relationships, behaviors, and event chains extracted directly from code and stored as `.architecture-model.yaml`.
- **Training Data Export** — Structured triples in `.architecture/` for LLM fine-tuning pipelines.

## Installation

```bash
pip install opencode-arch
```

With MCP server support (for AI agent integration):

```bash
pip install opencode-arch[mcp]
```

Requires Python 3.11+.

## Quick Start

```bash
# 1. Extract architecture from any Python repo
opencode-arch extract /path/to/your/repo

# 2. Check representativeness scores
opencode-arch metrics --last=1

# 3. Export training data
opencode-arch export-data
```

After extraction, your repo contains:

```
.architecture-model.yaml     # Component model (YAML)
.architecture/
├── manifest.json            # Full AST scan (modules, functions, imports)
└── metrics.json             # Representativeness scores + telemetry
```

## CLI

| Command | Purpose |
|---------|---------|
| `opencode-arch extract <repo>` | Extract architecture model from a repository |
| `opencode-arch generate <repo>` | Generate code with test-guided verification |
| `opencode-arch bench <repo1> <repo2> ...` | Benchmark extraction across multiple repos |
| `opencode-arch metrics` | View extraction history and scores |
| `opencode-arch export-data` | Export training corpus |

Options for `extract`:

```bash
opencode-arch extract /path/to/repo \
  --budget=4000 \        # Token budget for context compression
  --focus=all \          # Focus: "all", F-block ID, layer name
  --target-score=80      # Minimum validation score to accept
```

## MCP Integration

Register as an MCP server for use with AI coding agents:

```bash
opencode mcp add
```

### 7 Tools

| Tool | Purpose |
|------|---------|
| `architect_scan` | AST scanning — returns modules, functions, classes, imports |
| `architect_slice` | Token-compressed context (the core innovation) |
| `architect_validate` | Structural validation, returns score 0–100 |
| `architect_extract` | Store validated model + record telemetry |
| `architect_generate` | Run test suite against generated code |
| `architect_group` | Auto-group modules into logical components |
| `architect_check` | Verify representativeness (4 sub-scores) |

### Typical Agent Workflow

```
scan → slice → (agent produces YAML) → validate → check → extract
```

The agent calls `scan` to understand the repo, `slice` to get compressed context, produces an architecture model, then `validate` + `check` gate quality before `extract` persists it.

## How It Works

```
┌─────────────────────────────────────────────────┐
│  AI Agent (frontier model)                      │
│  Receives ~430 tokens of compressed context     │
│  Produces architecture YAML                     │
└────────────────────┬────────────────────────────┘
                     │ MCP Protocol
┌────────────────────▼────────────────────────────┐
│  opencode-arch (FastMCP server)                 │
│  scan → slice → validate → check → extract     │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│  architecture-model-standard (library)          │
│  AST scanning │ YAML parsing │ Validation       │
│  Context formatting │ Model slicing             │
└─────────────────────────────────────────────────┘
```

**Key design decision:** The agent IS the oracle. Tools never call external models — they provide compressed context to the frontier model already in the conversation.

## Benchmarks

Achieved automatically with no human tuning:

| Repository | Modules | Components | Overall Score |
|------------|---------|------------|---------------|
| FastAPI | 25 | 9 | 98.1% |
| Pydantic | 69 | 40 | 98.0% |
| httpx | 23 | 10 | 96.0% |
| Requests | 19 | 9 | 94.2% |
| Flask | 6 | 6 | 100.0% |
| Celery | 161 | 23 | 84.0% |

Scores are composite representativeness: file coverage × relationship accuracy × boundary coherence × behavioral coverage.

## Training Data

Each extraction produces a structured triple:

```
(.architecture-model.yaml, manifest.json, metrics.json)
```

This enables:
- Fine-tuning models on architecture extraction tasks
- Evaluating model quality with mechanical ground truth
- Building datasets across many repositories with `bench`

Export with:

```bash
opencode-arch export-data --format=jsonl
```

## Architecture Model Schema

```yaml
meta:
  project: my-project
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: APILayer
      status: ACTIVE
  capabilities:
    - id: CAP-F1
      name: RequestHandling
      status: ACTIVE
relationships:
  - from: COMP-1
    to: CAP-F1
    type: realizes
```

Relationship types: `realizes`, `uses`, `constrains`, `contains`, `triggers`, `depends_on`, `implements`, `exposes`.

## Development

```bash
git clone https://github.com/anomalyco/opencode-arch
cd opencode-arch
pip install -e ".[dev]"
pytest tests/ -v  # 278 tests, ~20s
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT
