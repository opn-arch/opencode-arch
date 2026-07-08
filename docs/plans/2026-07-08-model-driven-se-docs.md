# Model-Driven SE Document Generator — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Replace the heavyweight logs-db pipeline (PostgreSQL, pgvector, 7 stages) with a lightweight system that generates SE documentation directly from our proven-lossless architecture model + reality manifest.

**Architecture:** Split across two repos:
- `architecture-model-standard` — Templates, artifact selector, context assembler (schema layer)
- `opencode-arch` — CLI `docs` command, OpencodeRunner integration, validation (generation layer)

**Core Insight:** Our architecture model provides BETTER grounding than embeddings-based RAG because it has AST-exact signatures, not inferred ones. The 100% blind fidelity proves the model is a lossless behavioral representation.

**Tech Stack:** Python dataclasses, pytest, OpencodeRunner (opencode run subprocess), existing model/manifest APIs

---

## Phase 1: Context Assembly Layer (architecture-model-standard)

### Task 1: Artifact Selector (`src/architecture_model/artifacts/selector.py`)

**Files:**
- Create: `src/architecture_model/artifacts/__init__.py`
- Create: `src/architecture_model/artifacts/selector.py`
- Create: `tests/test_artifact_selector.py`

**What it does:**
Given an `ArchitectureModel`, determine which SE artifacts are appropriate to generate based on model richness. Not a hardcoded list of 32 — instead, model content drives selection.

**Selection rules:**
```python
@dataclass
class ArtifactSpec:
    id: str              # e.g. "api-reference"
    name: str            # e.g. "API Reference"
    category: str        # "architecture" | "design" | "operations" | "requirements"
    requires: list[str]  # what model content is needed: ["interfaces"], ["components", "layers"]
    priority: int        # 1=always if data exists, 2=recommended, 3=optional

def select_artifacts(model: ArchitectureModel, manifest: dict | None = None) -> list[ArtifactSpec]:
    """Return artifacts appropriate for this model's richness."""
    # For each artifact, check if model has the required entities
    # e.g. "api-reference" requires at least 1 interface
    # e.g. "deployment-view" requires components with layer allocations
```

**Acceptance criteria:**
- Given a model with only components and capabilities → selects ~5 basic artifacts
- Given a rich model (all entity types populated) → selects ~12 artifacts
- Given a model with no interfaces → does NOT select "api-reference"
- Pure function, no side effects, no I/O

---

### Task 2: Artifact Templates (`src/architecture_model/artifacts/templates.py`)

**Files:**
- Create: `src/architecture_model/artifacts/templates.py`
- Create: `tests/test_artifact_templates.py`

**What it does:**
Define 12 artifact templates with their section structure, generation prompts, and required model data. These are the "recipes" the LLM follows.

**Template structure:**
```python
@dataclass
class TemplateSection:
    heading: str         # "## Overview", "## Endpoints"
    source: str          # which model/manifest data feeds this section
    instructions: str    # LLM instructions for this section

@dataclass
class ArtifactTemplate:
    artifact_id: str     # matches ArtifactSpec.id
    filename: str        # output filename pattern, e.g. "api-reference.md"
    sections: list[TemplateSection]
    system_prompt: str   # role/context for the LLM

TEMPLATES: dict[str, ArtifactTemplate] = { ... }
```

**The 12 artifacts (derived from logs-db's 32, filtered to what model can ground):**
1. `system-overview` — architecture narrative (needs: meta, components, layers)
2. `component-catalog` — all components with interfaces (needs: components)
3. `api-reference` — interface details (needs: interfaces)
4. `capability-map` — functional decomposition (needs: capabilities)
5. `behavior-flows` — use case / workflow docs (needs: behaviors)
6. `constraint-register` — NFRs and design rules (needs: constraints)
7. `dependency-graph` — component relationships (needs: relationships)
8. `layer-architecture` — tier descriptions (needs: layers)
9. `deployment-view` — how components deploy (needs: components with layers)
10. `integration-guide` — how to connect (needs: interfaces, components)
11. `test-strategy` — testing approach (needs: manifest test data)
12. `metrics-dashboard` — code metrics summary (needs: manifest metrics)

**Acceptance criteria:**
- `TEMPLATES` dict has 12 entries
- Each template has at least 2 sections
- Each template references only valid model entity types
- Template lookup by artifact_id is O(1)

---

### Task 3: Context Assembler (`src/architecture_model/artifacts/context.py`)

**Files:**
- Create: `src/architecture_model/artifacts/context.py`
- Create: `tests/test_artifact_context.py`

**What it does:**
For a given artifact template + model + manifest, assemble the context string that will be included in the LLM prompt. This is the "data layer" — it extracts and formats relevant model/manifest data for each section.

**API:**
```python
def assemble_artifact_context(
    template: ArtifactTemplate,
    model: ArchitectureModel,
    manifest: dict | None = None,
    max_tokens: int = 4000,
) -> str:
    """Assemble formatted context for artifact generation.
    
    For each section in the template:
    1. Extract relevant data from model/manifest based on section.source
    2. Format it concisely (token-aware)
    3. Combine with section instructions
    
    Returns a structured prompt string ready for LLM consumption.
    """

def _extract_section_data(
    source: str,
    model: ArchitectureModel,
    manifest: dict | None,
) -> str:
    """Extract and format data for a single section source."""
```

**Source mappings:**
- `"components"` → format all components with their status, kind, file paths
- `"interfaces"` → format interfaces with operations, protocols
- `"capabilities"` → format capability tree
- `"behaviors"` → format behavior sequences
- `"constraints"` → format constraint register
- `"relationships"` → format relationship graph
- `"layers"` → format layer allocation
- `"manifest.metrics"` → format code metrics from manifest
- `"manifest.tests"` → format test inventory from manifest
- `"meta"` → project name, version, description

**Acceptance criteria:**
- Given a template + model → returns non-empty string
- Token budget is respected (output ≤ max_tokens)
- Missing data sources produce graceful "No data available" (not crash)
- Reuses `format_model_context()` from integrations where possible

---

### Task 4: Package Init + Exports

**Files:**
- Modify: `src/architecture_model/artifacts/__init__.py` (add exports)
- Modify: `src/architecture_model/__init__.py` (add artifacts to top-level API)

**What it does:**
Wire up the new package and expose its public API.

**Exports from `artifacts/__init__.py`:**
```python
from .selector import ArtifactSpec, select_artifacts
from .templates import ArtifactTemplate, TemplateSection, TEMPLATES
from .context import assemble_artifact_context
```

**Add to top-level `__init__.py`:**
```python
from .artifacts import select_artifacts, assemble_artifact_context, TEMPLATES
```

**Acceptance criteria:**
- `from architecture_model import select_artifacts` works
- `from architecture_model.artifacts import TEMPLATES` works
- Existing tests still pass (no regressions)
- Import cycle free

---

## Phase 2: Subsystem Decomposition Support

### Task 5: Subsystem-Level Selection (`src/architecture_model/artifacts/selector.py`)

**Files:**
- Modify: `src/architecture_model/artifacts/selector.py`
- Modify: `tests/test_artifact_selector.py`

**What it does:**
For complex systems, support generating docs per-subsystem. A "subsystem" is a functional block or decomposed unit (from `test_affinity_decompose`).

**API additions:**
```python
@dataclass
class SubsystemInfo:
    id: str
    name: str
    components: list[str]  # component IDs
    file_count: int
    test_count: int

def should_decompose(model: ArchitectureModel, manifest: dict) -> bool:
    """Determine if system is complex enough to warrant per-subsystem docs.
    
    Heuristic: >5 functional blocks OR >50 source files OR >20 components
    """

def select_subsystem_artifacts(
    subsystem: SubsystemInfo,
    model: ArchitectureModel,
) -> list[ArtifactSpec]:
    """Select artifacts appropriate for a subsystem (subset of system-level).
    
    Subsystems get: component-catalog, api-reference, behavior-flows, test-strategy
    They don't get: system-overview, layer-architecture, deployment-view
    """
```

**Acceptance criteria:**
- Small model (3 components) → `should_decompose()` returns False
- Large model (25 components, 80 files) → returns True
- Subsystem artifact selection is a strict subset of system-level
- Subsystem artifacts correctly filter to subsystem's components only

---

## Phase 3: Generation Command (opencode-arch)

### Task 6: CLI `docs` Command (`src/opencode_arch/cli/docs.py`)

**Files:**
- Create: `src/opencode_arch/cli/docs.py`
- Modify: `src/opencode_arch/cli/main.py` (add `docs` subcommand)
- Create: `tests/test_docs_cli.py`

**What it does:**
CLI command that orchestrates SE doc generation for a target project. Uses OpencodeRunner to send prompts to the agent. Pattern follows `regen_loop.py`.

**CLI interface:**
```
opencode-arch docs generate <project-path> [--output-dir docs/se/] [--artifacts api-reference,system-overview] [--model-path .architecture-model.yaml]
opencode-arch docs list <project-path>  # show which artifacts would be generated
opencode-arch docs validate <project-path> --docs-dir docs/se/  # validate existing docs
```

**Flow (generate):**
1. Load model from project (or `--model-path`)
2. Generate manifest via `generate_manifest()`
3. Call `select_artifacts(model, manifest)` to determine what to generate
4. For each artifact:
   a. Get template from `TEMPLATES[artifact_id]`
   b. Assemble context via `assemble_artifact_context(template, model, manifest)`
   c. Build prompt: system_prompt + context + "Generate this artifact"
   d. Call `OpencodeRunner.run(prompt, repo_path)`
   e. Write result to `output_dir/artifact_id.md`
5. Generate `index.md` linking all artifacts
6. Run validation pass

**Acceptance criteria:**
- `opencode-arch docs list .` prints selected artifacts with reasons
- `opencode-arch docs generate .` produces markdown files in output dir
- Each generated file has proper frontmatter (artifact_id, generated_at, model_version)
- Handles runner failures gracefully (logs error, continues to next)
- `--artifacts` flag filters to specific artifacts only

---

### Task 7: Integration Tests

**Files:**
- Create: `tests/test_docs_integration.py`

**What it does:**
Test the docs command end-to-end with a mocked OpencodeRunner. Verify prompt assembly, file writing, error handling.

**Test cases:**
1. `test_list_artifacts_for_model` — given a model, list shows correct artifacts
2. `test_generate_creates_files` — mock runner returns content, files created correctly
3. `test_generate_handles_runner_failure` — runner fails on one artifact, others still generated
4. `test_prompt_assembly` — verify the prompt sent to runner contains model context
5. `test_output_frontmatter` — generated files have correct metadata
6. `test_index_generation` — index.md links all generated artifacts
7. `test_artifact_filter` — `--artifacts` flag correctly filters

**Acceptance criteria:**
- All 7 tests pass
- Tests use mock runner (no real LLM calls)
- Tests use tmp directories (no filesystem pollution)

---

## Phase 4: Validation

### Task 8: Documentation Validator (`src/opencode_arch/cli/docs_validator.py`)

**Files:**
- Create: `src/opencode_arch/cli/docs_validator.py`
- Create: `tests/test_docs_validator.py`

**What it does:**
Validate generated docs against the reality manifest. Check that file paths mentioned exist, function names are real, component references match model, etc.

**API:**
```python
@dataclass
class ValidationIssue:
    artifact_id: str
    line: int
    issue_type: str  # "invalid_path", "unknown_function", "stale_reference"
    message: str
    severity: str    # "error", "warning"

@dataclass  
class DocsValidationResult:
    total_artifacts: int
    passed: int
    failed: int
    issues: list[ValidationIssue]

def validate_docs(
    docs_dir: Path,
    model: ArchitectureModel,
    manifest: dict,
) -> DocsValidationResult:
    """Validate generated documentation against model and manifest."""
```

**Validation rules:**
1. File paths mentioned in docs must exist in manifest's file inventory
2. Function/class names must appear in manifest's AST data
3. Component IDs must match model's component list
4. Interface references must match model's interfaces
5. Metrics claims must be within 10% of manifest values

**Acceptance criteria:**
- Catches invalid file path references
- Catches stale function references
- Produces structured JSON report
- Integrates with `opencode-arch docs validate` command

---

### Task 9: Full Test Suite Verification

**What it does:**
Run complete test suites for both repos, ensure no regressions.

```bash
# architecture-model-standard
pytest tests/ -v --ignore=tests/test_config_loader.py

# opencode-arch
pytest tests/ -v -m "not e2e"
```

**Acceptance criteria:**
- architecture-model-standard: 402+ tests pass (no regressions)
- opencode-arch: 157+ tests pass (no regressions)
- New tests all pass
- No import errors or circular dependencies

---

## Summary

| Phase | Tasks | Repo | New Files | New Tests |
|-------|-------|------|-----------|-----------|
| 1 | 1-4 | architecture-model-standard | 4 | ~20 |
| 2 | 5 | architecture-model-standard | 0 (modify) | ~5 |
| 3 | 6-7 | opencode-arch | 2 | ~10 |
| 4 | 8-9 | opencode-arch | 2 | ~8 |
| **Total** | **9** | **both** | **~8** | **~43** |

**Estimated time:** ~2-3 hours with subagent-driven development
