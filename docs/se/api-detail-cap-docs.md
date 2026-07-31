# API Detail — CAP-DOCS: SE Document Generation

## Overview

| Field | Value |
|-------|-------|
| ID | CAP-DOCS |
| F-Block | F1 (Core Workflows) |
| Priority | High |
| Realized by | COMP-CLI (`cli/docs.py`) |
| Actor | Developer via CLI |
| Constraint | CON-NO-HALLUCINATION |

---

## Primary API

### `run_docs_generate(repo_path, runner, output_dir=None, artifact_filter=None, model_path=None) -> DocsResult`

**Module:** `opencode_arch.cli.docs`

Generates SE documentation for a project. Selects which artifacts to produce based on model richness, then generates each via LLM with grounded context.

**Algorithm:**

1. Load architecture model (from `model_path` or `<repo>/.architecture-model.yaml`)
2. Generate reality manifest via `generate_manifest(repo_path)` (best-effort)
3. Call `select_artifacts(model, manifest)` to determine what to generate
4. If `artifact_filter` provided, intersect with selection
5. For each selected artifact:
   a. Get template from `TEMPLATES[artifact_id]`
   b. Assemble context via `assemble_artifact_context(template, model, manifest)`
   c. Build full prompt (context + generation instructions)
   d. Call `runner.run(prompt, repo_path)`
   e. Write result with YAML frontmatter to `output_dir/filename`
6. Generate `index.md` linking all generated artifacts
7. Return `DocsResult`

**Parameters:**

| Param | Default | Purpose |
|-------|---------|---------|
| `repo_path` | — | Project root directory |
| `runner` | — | `RunnerBackend` instance |
| `output_dir` | `<repo>/docs/se` | Where to write generated docs |
| `artifact_filter` | `None` | Subset of artifact IDs to generate |
| `model_path` | `None` | Override model path |

---

### `DocsResult` (dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `generated` | `list[str]` | Artifact IDs successfully generated |
| `failed` | `list[str]` | Artifact IDs that failed |
| `output_dir` | `str` | Path to output directory |
| `time_seconds` | `float` | Total elapsed time |
| `error` | `str | None` | Top-level error if whole run failed |

---

### `run_docs_list(repo_path, model_path=None) -> list[dict]`

Lists which artifacts would be generated for a project (dry-run).

Returns list of `{"id", "name", "category", "priority"}` dicts.

---

## Artifact Selection — `opencode_arch.artifacts.selector`

### `select_artifacts(model: ArchitectureModel, manifest: dict | None = None) -> list[ArtifactSpec]`

Pure function — no I/O. Determines which artifacts are appropriate based on model richness.

**Logic:** For each artifact in `ARTIFACT_REGISTRY`, check if ALL required entities exist in the model. Return matching artifacts sorted by priority then ID.

### `ARTIFACT_REGISTRY` (12 artifacts)

| ID | Name | Category | Requires | Priority |
|----|------|----------|----------|----------|
| `system-overview` | System Overview | architecture | components | 1 |
| `component-catalog` | Component Catalog | architecture | components | 1 |
| `api-reference` | API Reference | design | interfaces | 1 |
| `capability-map` | Capability Map | requirements | capabilities | 1 |
| `behavior-flows` | Behavior Flows | design | behaviors | 2 |
| `constraint-register` | Constraint Register | requirements | constraints | 2 |
| `dependency-graph` | Dependency Graph | architecture | components, relationships | 2 |
| `layer-architecture` | Layer Architecture | architecture | layers | 2 |
| `deployment-view` | Deployment View | operations | components, layers | 2 |
| `integration-guide` | Integration Guide | design | interfaces, components | 3 |
| `test-strategy` | Test Strategy | operations | manifest.tests | 3 |
| `metrics-dashboard` | Metrics Dashboard | operations | manifest.metrics | 3 |

### `should_decompose(model, manifest) -> bool`

Determines if system is complex enough for per-subsystem docs. Returns True if:
- More than 5 functional blocks, OR
- More than 50 source files in manifest, OR
- More than 20 components

### `get_artifact_spec(artifact_id: str) -> ArtifactSpec | None`

Lookup a single artifact spec by ID.

---

## Behavioral View: BEH-DOCS

**Trigger:** `opencode-arch docs generate [--repo path] [--artifacts id1,id2] [--output dir]`

**Key constraint:** CON-NO-HALLUCINATION — every claim in generated docs must trace to model/manifest data. The context assembly ensures only grounded data reaches the LLM.

**Sequence:**

```
Developer ──► CLI (docs generate)
                │
                ├─► load_model()
                ├─► generate_manifest() (best-effort)
                ├─► select_artifacts(model, manifest)
                │
                │   ┌─── FOR EACH artifact ──────────────┐
                │   ├─► get template (filename, structure)│
                │   ├─► assemble_artifact_context()       │
                │   ├─► build prompt (context + instructions)
                │   ├─► runner.run(prompt, repo_path)     │
                │   ├─► write markdown with frontmatter   │
                │   └────────────────────────────────────-┘
                │
                ├─► generate index.md
                │
Developer ◄── DocsResult
```
