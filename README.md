# opencode-arch

**Architecture extraction, validation, and lifecycle tooling for codebases — openAG edition.**

Scan a repository into a graph-native architecture model, mechanically score how well that model represents the code, and expose the whole surface to AI agents over MCP as ~60 `arch_*` tools.

![PyPI](https://img.shields.io/pypi/v/opencode-arch)
![Python](https://img.shields.io/pypi/pyversions/opencode-arch)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## Why

| Problem | Solution |
|---------|----------|
| Architecture docs drift from code | Mechanical representativeness scoring — know exactly when your model is wrong |
| AI agents burn tokens reading every file | Entity-scoped slices — read just the sub-doc for one node instead of the whole repo |
| No structured architecture data | A persisted, versioned v3 model graph with monotone generations you can diff |
| Manual component boundary decisions | Deterministic B-ROUND fixpoint auto-partitions modules into systems/components |

## The openAG model

The live engine is **openAG** — a graph-native successor to the earlier AMS flow. It works in two phases: **write the model once, then read it.**

- A **writer** (`arch_pipeline` or `arch_extract`) scans the source, runs the deterministic B-ROUND fixpoint, and persists the model.
- Every other `arch_*` tool is a **reader** over that persisted model.

Until a writer has run, readers raise `FileNotFoundError: openAG model dir not found/empty`.

Extraction is **Python-AST-only and coarse by design**: one System + one Component claiming every scanned file, refined by the fixpoint. There is no LLM enrichment loop and no per-stage quality score — scores come from the `arch_evaluate` / `arch_validate` readers.

After a writer runs, the target repo contains:

```
.architecture/
├── model/
│   └── model.v3.yaml        # the persisted graph-native model
└── generations/
    └── openAG-tool/         # monotone generation snapshots
```

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
# Launch an architecture-aware OpenCode session (scans + injects context)
opencode-arch

# Or target a specific repo
opencode-arch /path/to/your/repo
```

Or drive the model directly over MCP (the primary interface). The minimal loop:

```
arch_pipeline(repo_path)      # 1. WRITE the model (required, first)
arch_evaluate(repo_path)      # 2. overall health / score
arch_validate(repo_path)      # 3. schema + axis-lint score (0–100)
arch_decompose(repo_path)     # 4. inspect the System decomposition
```

## CLI

| Command | Purpose |
|---------|---------|
| `opencode-arch` | **Launch interactive session** (default — scans, injects context, opens OpenCode) |
| `opencode-arch launch [repo]` | Explicit launch form |
| `opencode-arch extract <repo>` | Extract an architecture model from a repository |
| `opencode-arch generate <repo>` | Generate code and run its tests (test-guided loop) |
| `opencode-arch bench <repo...>` | Benchmark extraction across multiple repos |
| `opencode-arch metrics` | View recorded metrics / learning curve / drift flags |
| `opencode-arch report` | Display the latest report card |
| `opencode-arch export-data` | Export a training corpus (JSONL) from `.architecture/` artifacts |

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

The server exposes the full `arch_*` surface (~60 tools). Every tool takes
`repo_path` (the target repo to operate on). Grouped by role:

### Writers — populate the model

| Tool | Purpose |
|------|---------|
| `arch_pipeline` | Run the B-ROUND fixpoint over source and commit a generation |
| `arch_extract` | Scan → extract a v3 model and commit a generation (lighter than pipeline) |
| `arch_author` | Forward-author a concept-phase model from requirements text |
| `arch_ingest` | Ingest a SourceGraph JSON into a deterministic model doc |
| `arch_grow` | Scoped forward-GROW operator from a root node |

### Scan & inspect — readers

| Tool | Purpose |
|------|---------|
| `arch_scan` | Module / import-edge inventory of the source tree (no model needed) |
| `arch_slice` | Entity-scoped sub-doc for a `node_id` (token-efficient context) |
| `arch_frontier` | Ready-promise node ids — the discovery entry point |
| `arch_owed` | Valence-owed-but-absent attributes for a `node_id` |
| `arch_gaps` | G-DELIVERY typed gaps for a `node_id` |
| `arch_health` | Graph-wide or per-node health projection |
| `arch_decompose` | System-level decomposition + split candidates |
| `arch_group` | Group modules by the model's A1 containment partition |
| `arch_round` | Run the B-ROUND least-fixpoint (whole-graph or node-scoped) |
| `arch_compliance` | openAG compliance report (matrix / axes / scoring) |

### Validate & gate

| Tool | Purpose |
|------|---------|
| `arch_validate` | Schema + axis-lint, returns a bounded score (0–100) |
| `arch_check` | Representativeness against the code ground graph |
| `arch_gate` | L2 development gate (owed + completeness gaps, scored) |
| `arch_evaluate` | Health rollup: coverage, score, promise rollup, requirement count |
| `arch_llm_audit` | Deterministic decomposition second-opinion audit |

### Change tracking & history

| Tool | Purpose |
|------|---------|
| `arch_diff` | Diff two model docs (defaults to git HEAD baseline) |
| `arch_history` | Generation timeline, node trajectory, or generation diff |
| `arch_commit_generation` | Record the current model as the next monotone generation |
| `arch_bind` | θ-crosswalk the latest generation onto the current model |

### Docs, export & views

| Tool | Purpose |
|------|---------|
| `arch_docs` | Generate openAG-shaped SE documentation |
| `arch_export` | Export the model as graphml / json-graph |
| `arch_view_project` / `arch_view_render` | Project / render the model into the viewer |
| `arch_slice_materialize` | Materialize an entity-scoped slice doc |
| `arch_artifact_plan` / `arch_artifact_rebuild` | Plan / rebuild derived artifacts |

### Requirements & feedback

| Tool | Purpose |
|------|---------|
| `arch_require` | Capture a MoSCoW-prioritized functional requirement |
| `arch_trace_requirements` | Trace requirements to model entities |
| `arch_correct` | Store a structured model correction |
| `arch_feedback` | Record user feedback / ratings / corrections |

### Decomposition primitives

| Tool | Purpose |
|------|---------|
| `arch_propose_cut` | Apply a partition-refinement proposal (gated write) |
| `arch_score_cut` | Score a candidate cut of a ground-graph slice |
| `arch_allocate_contract` | Allocate producer/consumer child contracts (A2 down-law) |
| `arch_integrate` | Run the B3 integration round over an interface's children |

### Lifecycle / packaging (generations)

| Tool | Purpose |
|------|---------|
| `arch_package_publish` | Publish the model as the next generation snapshot |
| `arch_package_load` | Load a published generation snapshot |
| `arch_package_list_generations` | List published snapshots |
| `arch_package_diff` | Diff two published snapshots |
| `arch_package_merge` | Three-way merge base/local/remote snapshots |
| `arch_package_stale` | Entities made stale by changed paths |
| `arch_package_children_add` | Append a child package ref |

### AI jobs & proposals

| Tool | Purpose |
|------|---------|
| `arch_proposal_validate` / `arch_proposal_apply` | Validate / apply a typed proposal |
| `arch_workorder_submit` | Persist an AI WorkOrder + draft tracking Job |
| `arch_job_get` / `arch_job_transition` / `arch_job_run` | Fetch / transition / execute an AI Job |
| `arch_work_issue` | Execute the comment→issue→dev ceremony loop |

### Proprioception & learning

| Tool | Purpose |
|------|---------|
| `arch_flags` | Proprioceptive anomaly flags |
| `arch_observe` | Raw runtime observation records |
| `arch_ingest_telemetry` | Append external observation events |
| `arch_lessons` | Mined lessons + reviewable proposal stubs |
| `arch_learn` / `arch_learn_approve` | Materialize / release a learning WorkOrder |
| `arch_mine` | Reservoir-mining pass over OpenCode sessions |
| `arch_stats` | Aggregate per-tool telemetry + model rollup |

### Typical Agent Workflow

```
arch_pipeline → arch_evaluate → arch_validate → arch_decompose
                                                     │
                      arch_frontier → (node_id) → arch_owed / arch_gaps / arch_slice
```

The agent writes the model once with `arch_pipeline`, checks overall health
with `arch_evaluate` / `arch_validate`, inspects the decomposition, then drills
into individual nodes via the node-scoped readers. On a coarse model the
frontier may be empty — get node ids from `arch_health` (`worst_offenders`) or
`arch_decompose` instead.

## How It Works

```
┌─────────────────────────────────────────────────┐
│  AI Agent (frontier model)                      │
│  Calls arch_* tools over MCP                    │
└────────────────────┬────────────────────────────┘
                     │ MCP Protocol
┌────────────────────▼────────────────────────────┐
│  opencode-arch (FastMCP server)                 │
│  writers populate .architecture/model/          │
│  readers project / score / diff that model      │
└────────────────────┬────────────────────────────┘
                     │ depends on
┌────────────────────▼────────────────────────────┐
│  openAG (graph-native engine)                   │
│  B-ROUND fixpoint │ generations │ promises       │
└─────────────────────────────────────────────────┘
```

**Key design decision:** extraction is deterministic. The writer derives the
model from the Python AST, not from an LLM — so results are reproducible and
the agent reasons over a stable graph.

For a complete tool-by-tool breakdown of what each `arch_*` tool delegates to
in the openAG engine and what OCA adds on top, see
[`docs/openag-mapping.md`](docs/openag-mapping.md) (PDF:
[`docs/openag-mapping.pdf`](docs/openag-mapping.pdf)).

## Skills

This repo ships OpenCode **skills** (under `skills/`) alongside the `arch_*`
MCP tools, so the guidance and the tools version together and cannot drift. A
drift test (`tests/test_skills_drift.py`) fails CI if a skill references a tool
that no longer exists or uses legacy vocabulary.

Install them into your global OpenCode skills directory:

```bash
./scripts/install-skills.sh
```

This **copies** each `skills/<name>/` into `~/.config/opencode/skills/<name>/`
(re-runnable; no dependency on this checkout staying on disk). The skills must
be global because the `arch_*` tools run against arbitrary target repos — a
project-local `.opencode/skills/` would only be found inside this worktree.

Shipped skills:

| Skill | Purpose |
|-------|---------|
| `extraction` | openAG write-once-then-read architecture extraction workflow |
| `generation` | Stub — code generation is not available in openAG; points to the real inspection tools |

**For later (deferred upgrade):** symlink instead of copy, so edits here are
picked up live without re-running the installer:

```bash
ln -snf "$(pwd)/skills/extraction" ~/.config/opencode/skills/extraction
```

Symlinking is the eventually-recommended mechanism (single source of truth,
zero drift) but is deferred until the skills stabilise.

## Development

```bash
git clone https://github.com/anomalyco/opencode-arch
cd opencode-arch
pip install -e ".[dev]"
pytest tests/ -v --ignore=tests/logs_db/test_client.py
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT
