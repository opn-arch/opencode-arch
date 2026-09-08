# Getting Started with opencode-arch

opencode-arch is an MCP server and CLI that extracts architecture models from codebases using AI agents. It compresses repository structure into minimal token budgets, enabling frontier models to produce high-quality architecture extractions.

## Installation

```bash
pip install opencode-arch
```

Requires Python 3.11+ and the `architecture-model-standard` package (installed automatically as a dependency).

## Your First Extraction

Run the extract command against any Python project:

```bash
opencode-arch extract /path/to/your/project
```

### What happens

1. **AST Scan** — Parses all Python files to extract modules, functions, classes, and imports
2. **Module Grouping** — Groups related modules into logical components using subdirectory, name-prefix, and import affinity signals
3. **Model Building** — The AI agent produces a YAML architecture model with components, capabilities, and relationships
4. **Representativeness Check** — Verifies the model against code reality (file coverage, relationship accuracy, boundary coherence)
5. **Persistence** — Stores the model and artifacts to `.architecture/`

### Expected output

```
Scanning repository...
  Found 42 modules, 187 functions, 31 classes
Grouping modules into components...
  Identified 8 component groups
Building architecture model...
  Agent produced model with 8 components, 3 capabilities, 14 relationships
Validating model...
  Validation score: 87/100
Checking representativeness...
  File coverage: 95%
  Relationship accuracy: 100%
  Boundary coherence: 88%
Stored: .architecture-model.yaml
Done.
```

## Understanding the Output

### `.architecture-model.yaml`

The primary output — a structured architecture model containing:
- **Components** — logical groupings of source modules
- **Capabilities** — high-level features the system provides
- **Relationships** — how components interact (realizes, uses, depends_on, etc.)

### `.architecture/manifest.json`

The detailed AST scan results: every module, function, class, and import edge discovered during analysis. This is the "ground truth" used for validation.

### `.architecture/metrics.json`

Quality scores from validation and representativeness checks, plus manifest-level metrics (module count, complexity distribution, etc.).

## Reading Metrics

The representativeness check produces four sub-scores:

| Metric | Description | Target |
|--------|-------------|--------|
| **File coverage** | % of source files mapped to at least one component | 100% |
| **Relationship accuracy** | % of model relationships backed by real import edges in code | 100% |
| **Boundary coherence** | Average internal cohesion of component file groupings (files within a component should import each other more than external files) | 100% |
| **Behavioral coverage** | % of complex functions (cyclomatic complexity > threshold) with captured behavior in the model | 100% |

A good extraction scores 80+ on validation and 90%+ on file coverage and relationship accuracy.

## Using with AI Agents (MCP)

Register opencode-arch as an MCP server so AI agents can use its tools directly:

```bash
opencode mcp add opencode-arch -- python -m opencode_arch.mcp.server
```

This exposes 7 tools to the agent:

| Tool | Purpose |
|------|---------|
| `architect_scan` | Generate AST manifest from a repository |
| `architect_slice` | Compress repo context into a token budget |
| `architect_validate` | Validate a YAML model for structural correctness |
| `architect_extract` | Store a validated model + record telemetry |
| `architect_generate` | Run tests against generated code |
| `architect_group` | Group modules into logical components |
| `architect_check` | Verify model representativeness against code |

The agent uses these tools in sequence: scan → group → slice → (produce model) → validate → check → extract.

## Next Steps

- [Collecting Training Data](training-data.md) — use opencode-arch to build fine-tuning datasets
- [Architecture Refresh Templates](templates/README.md) — opt-in pre-commit hook and GitHub Actions workflow to keep the model in sync with code
- [Contributing](../CONTRIBUTING.md) — how to develop and extend opencode-arch
