# opencode-arch

## Origin

OpenCode MCP extension extracted from the architecture-model-standard project. Provides **context compression tools** (the "token broker") that enable LLM agents to reason about codebases with minimal token expenditure.

## Purpose

An MCP server that wraps `architecture-model-standard` APIs to provide 5 tools for architecture-driven development. The core value proposition is **token arbitrage**: compress a full repository's structure into ~430 tokens of dense context, enabling the agent to produce high-quality architecture extractions without reading every file.

**Key insight:** The agent IS the oracle. Tools don't call external models — they provide compressed context to the frontier model already present in the conversation.

## Architecture

```
Agent (frontier model in OpenCode)
  ↕ MCP Protocol
opencode-arch server (FastMCP)
  ├── architect_scan    → wraps generate_manifest()
  ├── architect_slice   → wraps format_model_context() / slicer
  ├── architect_validate → wraps validate_model()
  ├── architect_extract → stores agent output + telemetry
  └── architect_generate → runs pytest on generated code
        ↓
architecture-model-standard (library)
  ├── manifest/generator.py  — AST scanning
  ├── core/parser.py         — YAML→ArchitectureModel
  ├── core/validator.py      — structural validation (0-100)
  ├── core/slicer.py         — model subsetting
  └── integrations/llm_context.py — context formatting
```

## The 6 MCP Tools

### 1. `architect_scan(repo_path: str) -> dict`
Generates a reality manifest via AST scanning. Returns modules, functions, classes, imports, metrics, functional blocks, and `suggested_components` (auto-grouped modules).

**When to use:** First step in any extraction — understand what's in the repo.

### 2. `architect_slice(repo_path: str, focus: str, budget: int, detail: str) -> str`
The core token-arbitrage function. Compresses a repository into a dense context string within the token budget.

- If `.architecture-model.yaml` exists: uses model + slicer + formatter (rich path)
- Otherwise: falls back to manifest-based compact YAML

**Parameters:**
- `focus`: "all", F-block ID ("F1"), layer name, or artifact name ("icd")
- `budget`: token budget (default 4000, ~16K chars)
- `detail`: "minimal", "standard", or "full"

**When to use:** Before any reasoning about architecture — get compressed context.

### 3. `architect_validate(model_yaml: str) -> dict`
Validates an architecture model for structural correctness.

**Returns:** `{score, issues, entity_count, relationship_count, is_valid}`

**When to use:** Quality gate after producing a model. Target score: 80+.

### 4. `architect_extract(repo_path: str, model_yaml: str, context_tokens: int) -> dict`
Stores a validated architecture model extraction. Called AFTER the agent produces YAML.

**Returns:** `{stored, score, issues, path, telemetry_recorded}`

**When to use:** After agent produces + validates a model — persist it.

### 5. `architect_generate(repo_path: str, test_command: str) -> dict`
Runs the repository's test suite against generated code.

**Returns:** `{passed, pass_rate, total_tests, passed_tests, failures}`

**When to use:** Quality gate for code generation — verify generated code passes tests.

### 6. `architect_group(repo_path: str, target_groups: int) -> dict`
Groups repository modules into logical architecture components using multi-signal affinity (subdirectory, name-prefix, imports).

**Parameters:**
- `target_groups`: Desired number of groups (0 = auto-calculate)

**Returns:** `{groups: [{name, files, file_count, primary_file}], total_modules, total_groups}`

**When to use:** After scan, before extraction — get suggested component boundaries.

### 7. `architect_check(repo_path: str, model_yaml: str) -> dict`
Verifies model representativeness against code reality using three mechanical sub-scores.

**Returns:** `{file_coverage, relationship_accuracy, boundary_coherence, overall, uncovered_files, unverified_relationships, low_coherence_components}`

**Sub-scores:**
- `file_coverage`: % of source files mapped to components (target: 100%)
- `relationship_accuracy`: % of model relationships backed by real import edges (target: 100%)
- `boundary_coherence`: avg internal cohesion of component file groupings (target: 100%)

**When to use:** After extraction — verify the model is 100% representative before accepting it.

## Phase 2 Lifecycle Tools (18 new)

Phase 2 (branch `feat/phase2-lifecycle`) added **18 MCP tools** covering the full architecture lifecycle — packaging, views, artifact rebuild, and an AI/workorder execution loop. These live in `mcp/tools/lifecycle/` and `mcp/tools/ai/` and do NOT modify any of the 7 core tools above (per Phase 2 exit criterion #4).

### Lifecycle (12 tools, `mcp/tools/lifecycle/`)
- `architect_package_publish` — publish current model as a versioned package generation
- `architect_package_load` — load a published package (by digest / generation)
- `architect_package_list_generations` — enumerate available generations
- `architect_package_diff` — structural diff between two generations
- `architect_package_stale` — detect drift vs. current code
- `architect_package_children_add` — federate a child package (`add_root`)
- `architect_package_merge` — merge child packages into a parent view
- `architect_slice_materialize` — materialize a slice as a standalone package
- `architect_view_project` — project an architecture view (context/components/etc.)
- `architect_view_render` — render a projected view (svg/png/mermaid)
- `architect_artifact_plan` — plan artifact rebuild set
- `architect_artifact_rebuild` — execute artifact rebuild

### AI / Workorder (6 tools, `mcp/tools/ai/`)
- `architect_workorder_submit` — submit a workorder (unit of proposed change)
- `architect_job_get` — inspect a job's current state
- `architect_job_transition` — advance a job's lifecycle state
- `architect_job_run` — execute a job (with fixture or real proposer)
- `architect_proposal_validate` — validate a proposal against the model
- `architect_proposal_apply` — apply a validated proposal (dry-run or real)

### Supporting modules
- `lifecycle_bridge/` — thin adapter to `architecture-model-standard`'s lifecycle APIs. Keeps MCP tools decoupled from library churn.
- `lifecycle_exec/` — execution primitives with **zero MCP dependencies** (unit-testable standalone): `paths`, `rebuild`, `worker`, `apply`, `merge`, `federation`.
- `mcp/envelope.py` — shared request/response envelope + error taxonomy for all lifecycle tools.
- CLI `lifecycle` and `ai` subcommand groups mirror the MCP surface.

Every state change (publish, transition, apply, rebuild) emits a journal event.

### `architect_docs` as sugar over `rebuild_artifacts` (Phase 1)

`architect_docs(repo_path, formats="all")` (defined at
`src/opencode_arch/mcp/server.py:281`) is the legacy entry point for
generating the SE document family (ConOps, ICD, component specs, use
cases, functional/logical architecture, requirements analysis, V&V,
operations/maintenance manuals, risk assessment, interface spec,
artifact traceability). After the Phase 1 model → view mapping work,
it becomes **sugar over `architect_artifact_rebuild`**: each requested
`format` maps to a fixed `(ModelSlice, ViewSpec, ArtifactSpec)` triple
defined in `src/opencode_arch/mcp/tools/docs_specs.py`, and the tool
delegates to the substrate pipeline
`materialize → project → render → rebuild`. This is the minimum-
invasive mapping — no `generate_docs` refactor — chosen to keep
callers of `architect_docs` working unchanged while the substrate
becomes the single artifact path.

Freshness metadata rides on every rendered artifact via the
`DiagramSpec.freshness` / `.revision` fields stamped inside `project()`
(see `architecture_model.lifecycle.view_projection:189-194`).
`architect_evaluate` exposes a `freshness_summary` key of shape
`{fresh, stale, unknown, pending}` counting the per-artifact status.
In Phase 1 all values report as `unknown` because the freshness stamp
is in-memory only — per-artifact `<id>.provenance.json` sidecars are
deferred to Phase 2 Task 28. See
`../architecture-model-standard/docs/plans/2026-09-08-phase-1-substrate-and-liveness.md`
for the full Phase 1 plan.

### Model → view mapping Phase 2 feedback wiring

Phase 2 of the model → view mapping design (AMS schema 2.1 + feedback
journals) added three cross-cutting integrations on the OCA side. All
are **fail-soft**: journal-write errors never fail the parent tool.

- **Gates journal.** `architect_gate` (MCP tool at
  `src/opencode_arch/mcp/tools/gate.py`) appends a `GateEvent`
  (`gate_id="architect_gate"`, `outcome` derived from
  `phase_requirements_met`, `findings=tuple(issues)`) to
  `.architecture/gates.jsonl` after computing `next_steps`.
- **Drift journal.** `architect_pipeline`
  (`src/opencode_arch/mcp/tools/pipeline.py`) calls
  `_append_drift_snapshot(root)` after `_write_sil_snapshots`. It loads
  `.architecture-model.yaml` and computes four drift kinds locally —
  `broken_ref`, `unrealized_capability`, `orphan`, `missing_impl` —
  then appends to `.architecture/drift.jsonl`.
- **Test-results ingestion.** New CLI `opencode-arch feedback
  ingest-junit <xml> [--repo-path .] [--suite NAME]` calls
  `architecture_model.feedback.junit_ingest.ingest_junit(path, suite=...)`
  and appends the batch via `test_results.append(repo, batch)` to
  `.architecture/test_results.jsonl`. Wired in
  `src/opencode_arch/cli/feedback.py` and dispatched from
  `src/opencode_arch/cli/main.py`.

See `../architecture-model-standard/docs/plans/2026-09-08-phase-2-schema-and-semantic-content.md`
for the full Phase 2 plan and the AMS-side schema/journal contracts.

## Package Structure

```
src/opencode_arch/
├── __init__.py
├── cli/
│   ├── __init__.py
│   ├── main.py           — argparse entry point (opencode-arch command)
│   ├── extract.py        — run_extract() loop
│   ├── generate.py       — run_generate() loop
│   ├── bench.py          — run_bench() multi-repo
│   ├── metrics.py        — show_metrics() display
│   └── prompts.py        — prompt templates for agent
├── context/
│   └── __init__.py
├── mcp/
│   ├── __init__.py
│   ├── envelope.py       — shared request/response envelope + error taxonomy (Phase 2)
│   ├── server.py         — FastMCP server (registers core + lifecycle + AI tools)
│   └── tools/
│       ├── __init__.py
│       ├── scan.py       — scan_repository()
│       ├── slice.py      — slice_context()
│       ├── validate.py   — validate_architecture()
│       ├── extract.py    — store_extraction()
│       ├── generate.py   — run_tests_on_generated_code()
│       ├── group.py      — group_repository()
│       ├── check.py      — check_representativeness()
│       ├── lifecycle/    — 12 Phase 2 lifecycle tools (package_*, slice_materialize,
│       │                   view_project, view_render, artifact_plan, artifact_rebuild)
│       └── ai/           — 6 Phase 2 AI/workorder tools (workorder_submit, job_get,
│                           job_transition, job_run, proposal_validate, proposal_apply)
├── lifecycle_bridge/     — thin adapter to architecture-model-standard lifecycle APIs (Phase 2)
├── lifecycle_exec/       — MCP-free execution primitives (Phase 2)
│   ├── paths.py          — workspace layout resolver
│   ├── rebuild.py        — artifact rebuild planner/executor
│   ├── worker.py         — job execution driver
│   ├── apply.py          — proposal application (dry-run + real)
│   ├── merge.py          — package merge logic
│   └── federation.py     — child-package federation
├── runner/
│   ├── __init__.py
│   ├── base.py           — RunResult, RunnerBackend protocol
│   └── opencode.py       — OpencodeRunner (subprocess)
└── telemetry/
    ├── __init__.py
    ├── store.py          — TelemetryStore (SQLite)
    └── recorder.py       — record_invocation() (async)

skills/
├── extraction/SKILL.md   — Architecture extraction workflow
└── generation/SKILL.md   — Test-guided code generation workflow

opencode.json             — OpenCode extension manifest
```

## Telemetry

SQLite-backed telemetry records every tool invocation:
- `tool`: which tool was called
- `repo`: target repository name
- `context_tokens`: how many tokens of context were used
- `output_quality`: validation score (0-100)
- `iterations`: how many attempts needed

Default DB location: `~/.opencode-arch/telemetry.db`

Future use: optimize context budgets and prompt strategies based on what works.

## Development

### Prerequisites
- Python 3.11+
- `architecture-model-standard` package installed (>= 0.3.0)

### Setup
```bash
# Uses the architecture-model-standard venv
cd /Users/baigm2/Documents/Projects/opencode-arch
pip install -e ".[dev]"
```

### Running tests
```bash
pytest tests/ -v
```

Current: **278 tests passing** (~20s)

### Test breakdown
| File | Tests | Covers |
|------|-------|--------|
| test_scan.py | 4 | scan_repository() |
| test_slice.py | 5 | slice_context() |
| test_mcp_validate.py | 4 | validate_architecture() |
| test_mcp_extract.py | 4 | store_extraction() |
| test_generate.py | 4 | run_tests_on_generated_code() |
| test_telemetry.py | 5 | TelemetryStore + recorder |
| test_integration.py | 2 | Full scan→slice→validate→extract flow |

## Design Decisions

1. **No external model calls** — the agent IS the oracle. Tools provide context only.
2. **Token arbitrage** — compress full repo into ~430 tokens for effective reasoning.
3. **Telemetry for learning** — record what works, optimize prompts and budgets over time.
4. **Graceful degradation** — if no `.architecture-model.yaml` exists, falls back to manifest.
5. **MCP optional** — tools work as standalone async functions even without mcp package.
6. **Validation as quality gate** — store only validates + persists, never blocks on score.

## Schema Format (for architect_extract)

The architecture model YAML follows this structure:
```yaml
meta:
  project: my-project
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: MyComponent
      status: ACTIVE  # ACTIVE | PLANNED | DEPRECATED
  capabilities:
    - id: CAP-F1
      name: MyCapability
      status: ACTIVE
  # Also: layers, behaviors, interfaces, constraints, actors
relationships:
  - from: COMP-1
    to: CAP-F1
    type: realizes  # realizes | uses | constrains | contains | triggers | depends_on | implements | exposes
```

**Important:** Entities must be nested under the `entities:` key (not top-level).

## CLI (`opencode-arch`)

### Setup
```bash
pip install -e .        # installs the opencode-arch command
opencode mcp add        # register MCP server with OpenCode (one-time)
```

### Commands

```bash
# Extract architecture from a repository (uses OpenCode as the agent):
opencode-arch extract /path/to/repo --budget=4000 --focus=all --target-score=80

# Generate code with test verification:
opencode-arch generate /path/to/repo --max-iter=3

# Benchmark extraction on multiple repos:
opencode-arch bench /path/to/repo1 /path/to/repo2 --output=metrics.json

# View recorded metrics:
opencode-arch metrics --tool=extract --last=10
```

### How it works

The CLI delegates the "thinking" step to OpenCode via subprocess (`opencode run`), then validates/stores/measures locally:

```
opencode-arch extract <repo>
  → builds prompt with instructions
  → calls: opencode run "<prompt>" --dir <repo>
  → parses YAML from agent output
  → validates via architecture-model-standard
  → stores .architecture-model.yaml
  → records telemetry (score, tokens, time)
  → prints results
```

### Runner backends

The CLI uses a pluggable runner protocol:
- **OpencodeRunner** (default) — subprocess `opencode run`
- **Custom** (future) — swap in your own model via `RunnerBackend` protocol

```python
# To add your own model:
from opencode_arch.runner.base import RunResult, RunnerBackend

class MyRunner:
    async def run(self, prompt: str, repo_path: str) -> RunResult:
        # Call your model here
        return RunResult(output=yaml_str, exit_code=0, success=True)
```

## Related Repos

| Repo | Purpose | Status |
|------|---------|--------|
| `architecture-model-standard` | Schema, validator, CLI, manifest generator | v0.3.0, 2918 tests (Phase 1 escalations landed on `feat/curated-se-views`) |
| `opencode-arch` | MCP extension (this repo) | v0.4.0, 917 tests (2 pre-existing failures documented) |
| `arch-agent` | Training pipeline + surrogate model | v0.1.0, 574 tests |

**AMS API adoption (2026-09-05, branch `feat/ams-api-adoption`):** consumed new public APIs from architecture-model-standard Phase 1 escalations:
- `generation_dir` (public replacement for `_generation_dir`) — adopted at 4 call sites across `mcp/tools/lifecycle/` and `cli/lifecycle.py`.
- `current_root_digest(pkg)` — adopted in `lifecycle_exec/apply.py` for CURRENT-generation digest reads.
- `apply_model_patch` (in `architecture_model.ai`) — evaluated; local `_apply_model_patch` retained (divergent contracts: dict vs dataclass, InvalidProposalError vs ParseError, dry-run wrapper). Documented in-file.
- `MaterializedSlice.to_dict()` — evaluated; local `slice_materialize.py` response contract adds `digest`/`persisted_path` fields, so adoption would change the MCP response shape. Retained.
- `WorkOrder.build(...)` — not applicable; opencode-arch only uses `WorkOrder.from_dict(...)`, never direct construction.
- `Provenance.proposal_id` auto-derive — already effectively in use; all 5 sites omit `proposal_id`.

## Instructions for Development

- Use TDD: write failing tests first, then implement
- All changes must pass existing tests (no regressions)
- Run tests: `pytest tests/ -v` (278 tests, ~20s)
- The `architecture-model-standard` package is a dependency — don't duplicate its code
- Telemetry failures should never block tool operation (swallow exceptions)
- MCP server import is wrapped in try/except — tools work without mcp package
- Integration tests simulate the agent's role (produce YAML, then store/validate)
- CLI tests mock the runner (don't actually call `opencode run`)

## Comment→Issue→Dev Loop (Plan A)

Closes the loop from a user comment on a rendered lifecycle artifact all the way to a committed model change and a closed logs-db Issue.

**Flow:**
1. **Capture** — `architecture-model comment <artifact-id> --view-id ... --slice-id ... --package-id ... --revision ... --body ... --author ...` writes a `CommentStub` to `.architecture/comments/` and appends a `comment.capture` journal event. (CLI lives in `architecture-model-standard`.)
2. **Sync** — `architect_sync` now pushes captured comments to logs-db, creating Issues (idempotent via `external_key=comment_id`). Implemented by `opencode_arch.mcp.tools.sync._push_comments` and wired into the existing `sync_findings` under key `"comments_pushed"`. Journals `comment.sync`.
3. **Work** — `architect_work_issue(repo_path, *, issue_id, dry_run=False, force=False, proposer=None)` MCP tool:
   - Pulls Issue from logs-db, loads local stub (journals `issue.pull`).
   - Short-circuits if a completed Job already exists for the same `comment_id` (idempotent).
   - Builds a WorkOrder (journals `workorder.from_issue`), runs the configured proposer, validates + applies the resulting `ModelPatch` (publishes a new generation).
   - On non-dry-run success: soft-gates via progress comment, commits the change with trailers `Issue:`, `Comment:`, `Session:`, `Model-Revision-From/To:`, `Model-Diff-Digest:`, and closes the Issue (journals `issue.close`).
4. **Proposer resolution** — `.architecture/ai/proposer_config.yaml` with `plugin: module.path:function_name` selects the callable. Plan A ships a fake proposer for tests; Plan B replaces it with a real `LLMProvider` adapter.

**Minimal usage:**
```bash
architecture-model comment art-1 --view-id v-1 --slice-id s-1 \
    --package-id p-1 --revision 0000001 \
    --body "COMP-2.5 missing constraint" --author reviewer
# → prints comment_id, e.g. cmt_...
# Then, from an OCA-aware MCP client:
architect_sync(repo_path=".")               # pushes comments → creates Issue
architect_work_issue(repo_path=".", issue_id=<n>)  # closes the loop
```

The `LOGS_DB_URL` env var overrides the default logs-db endpoint. `OPENCODE_SESSION_ID` (set by OpenCode) is captured into the WorkOrder and commit trailers for traceability.

<!-- opencode-arch:start -->
# Architecture (auto-managed by opencode-arch)

**Model:** 6 components | 16 relationships
**Score:** 58.3% (FC=40% RA=80% BC=13% BV=100%)
**Codebase:** 80 modules | 125 import edges

## Component Map

## Architecture: 6 components
- **CLI Commands** (COMP-CLI): src/opencode_arch/cli/main.py, src/opencode_arch/cli/extract.py, src/opencode_arch/cli/generate.py
- **MCP Server** (COMP-MCP): src/opencode_arch/mcp/__main__.py, src/opencode_arch/mcp/server.py, src/opencode_arch/mcp/tools/scan.py
- **OpenCode Runner** (COMP-RUNNER): src/opencode_arch/runner/base.py, src/opencode_arch/runner/opencode.py
- **Learning Loop** (COMP-LEARNING): src/opencode_arch/learning/classifier.py, src/opencode_arch/learning/adapter.py, src/opencode_arch/learning/assessor.py
- **Telemetry Store** (COMP-TELEMETRY): src/opencode_arch/telemetry/store.py, src/opencode_arch/telemetry/recorder.py
- **Prompt Templates** (COMP-PROMPTS): src/opencode_arch/prompts/regen.py, src/opencode_arch/prompts/extract.py

## Development Guidelines

- Use `architect_slice` for focused context on specific components
- Use `architect_check` after significant changes to verify model accuracy
- Use `architect_require` to capture functional requirements from discussion
- Use `architect_feedback` to record corrections or rate tool quality
- Components are auto-grouped by import affinity — respect boundaries
<!-- opencode-arch:end -->
