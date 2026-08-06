# F-Block Accuracy, Multi-Language Generalization, Requirements Traceability & Pipeline Improvements

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement F-block quality metrics, LLM audit infrastructure, requirements traceability, fix silent pipeline failures, close the interface gap, and add new doc generators.

**Architecture:** Six independent workstreams (WS-A through WS-F) across two repos. WS-A/B/C implement the discussion.md design. WS-D/E/F implement the prior Tier 1-3 backlog. WS-A is fully deterministic (architecture-model-standard only). WS-B/C require LLM cache infrastructure (shared prereq WS-B0). WS-D/E/F are opencode-arch only.

**Tech Stack:** Python 3.12, pytest, architecture-model-standard (deterministic core), opencode-arch (MCP tools + CLI), OpencodeRunner (subprocess to `opencode run`)

**Repos:**
- `ams` = `/Users/baigm2/Documents/Projects/architecture-model-standard/`
- `oa` = `/Users/baigm2/Documents/Projects/opencode-arch/`

**Test commands:**
- ams: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`
- oa: `/opt/anaconda3/bin/python -m pytest tests/test_export_tool.py tests/test_quality.py tests/test_stats_correct.py tests/test_docs_tool.py tests/test_entity_fallback.py tests/test_decompose_tool.py tests/test_behavior_flow_wiring.py -v`

**Pre-existing test failures (do not fix):**
- ams: `test_config_loader.py` (always skip), `test_docs_gen.py::TestHealthReport::test_includes_confidence`, `test_includes_components`
- oa: `test_scan.py`, `test_extract_from_code.py`, `test_docs_cli.py`, `test_integration.py`, `test_check_tool.py`

---

## Dependency Graph

```
WS-A (F-Block Accuracy)          — independent, ams only
WS-B0 (LLM Cache Infra)         — prereq for WS-B and WS-C
WS-B (LLM Audit)                — depends on WS-B0
WS-C (Requirements Traceability) — depends on WS-B0, partially on WS-A (for coverage integration)
WS-D (Silent Failure Fix)       — independent, oa only
WS-E (Interface Gap)            — independent, ams + oa
WS-F (New Doc Generators)       — independent, ams + oa
```

**Parallelizable groups:**
- Group 1: WS-A + WS-B0 + WS-D + WS-E + WS-F (all independent)
- Group 2: WS-B + WS-C (after WS-B0 completes)

---

## WS-A: F-Block Accuracy Metrics (architecture-model-standard)

### Task A1: Deterministic tie-break in `auto_assign_f_blocks`

**Files:**
- Modify: `ams/src/architecture_model/core/fblock_assign.py:52`
- Test: `ams/tests/test_fblock_assign.py` (create or extend)

**What:** Add secondary sort key `(degree desc, component.id asc)` on line 52 so identical degree components have deterministic ordering.

**Test:** Create two components with identical degree, verify assignment is alphabetical by ID regardless of input order.

### Task A2: Modularity score (Newman's Q)

**Files:**
- Create: `ams/src/architecture_model/core/fblock_quality.py`
- Test: `ams/tests/test_fblock_quality.py`

**What:** Implement `compute_modularity(model) -> float` using Newman's modularity formula over `depends-on` edges. Each F-block is a community. Returns Q in [-0.5, 1.0].

**Interface:**
```python
def compute_modularity(model: ArchitectureModel) -> float: ...
def compute_conductance(model: ArchitectureModel) -> dict[str, float]: ...  # per F-block
def compute_fblock_quality(model: ArchitectureModel) -> FBlockQuality: ...  # aggregated
```

**`FBlockQuality` dataclass:**
```python
@dataclass
class FBlockQuality:
    modularity: float          # Newman's Q
    conductance: dict[str, float]  # block_id -> conductance
    intra_inter_ratio: float
    agreement_rate: float | None   # None if no directory info
    orphan_rate: float
    cluster_balance: float     # Gini coefficient
    cross_block_cycle_ratio: float
```

**Tests:** (1) Known graph with clear clusters → Q > 0.3, (2) single-cluster → Q = 0, (3) disconnected graph → orphan_rate = 1.0, (4) bidirectional cross-block edge → cycle_ratio > 0, (5) balanced clusters → low Gini.

### Task A3: Per-component provenance tagging

**Files:**
- Modify: `ams/src/architecture_model/core/fblock_assign.py`
- Modify: `ams/src/architecture_model/core/types.py` (add `FBlockProvenance` dataclass)
- Test: extend `ams/tests/test_fblock_quality.py`

**What:** After `auto_assign_f_blocks` runs, attach `fblock_provenance` dict to each component (stored in component's `tags` or a new optional field). Contains `source`, `confidence` (formula over A2 metrics), `metrics` sub-dict, `content_hash`, `computed_at`.

**Confidence formula:** `confidence = 0.4 * (1 - conductance) + 0.3 * (1 if agreement else 0) + 0.2 * modularity_contribution + 0.1 * (1 - orphan_flag)`

### Task A4: Wire into coverage report (dimension 6)

**Files:**
- Modify: `ams/src/architecture_model/core/coverage.py`
- Test: extend `ams/tests/test_coverage.py`

**What:** Add `_check_fblock_quality(model) -> CoverageCheck` calling `compute_fblock_quality()`. Returns score based on modularity + mean conductance. Add to `coverage_report()` results.

### Task A5: Agreement rate — directory vs. clustering comparison

**Files:**
- Extend: `ams/src/architecture_model/core/fblock_quality.py`
- Test: extend `ams/tests/test_fblock_quality.py`

**What:** `compute_agreement_rate(model, config) -> float` — runs `auto_assign_f_blocks` independently, compares its output to existing directory-derived `f_block` assignments, returns % agreement.

---

## WS-B0: LLM Cache Infrastructure (opencode-arch — prereq for WS-B, WS-C)

### Task B0.1: LLM cache layer

**Files:**
- Create: `oa/src/opencode_arch/llm/__init__.py`
- Create: `oa/src/opencode_arch/llm/cache.py`
- Test: `oa/tests/test_llm_cache.py`

**What:** Content-hash-based cache for LLM calls via OpencodeRunner.

**Interface:**
```python
@dataclass
class CachedResult:
    output: str
    model: str
    prompt_hash: str
    content_hash: str
    cached: bool
    timestamp: str

class LLMCache:
    def __init__(self, cache_dir: Path): ...  # default: ~/.opencode-arch/llm-cache/
    def get(self, content_hash: str, prompt_hash: str) -> CachedResult | None: ...
    def put(self, content_hash: str, prompt_hash: str, output: str, model: str) -> None: ...
    def clear(self) -> int: ...  # returns count deleted

async def cached_llm_call(
    runner: RunnerBackend,
    prompt: str,
    content_hash: str,
    prompt_template_hash: str,
    repo_path: str,
    cache: LLMCache | None = None,
) -> CachedResult: ...
```

**Storage:** JSON files in `{cache_dir}/{content_hash[:2]}/{content_hash}.json`, keyed by `(content_hash, prompt_hash)`.

**Tests:** (1) Cache miss → calls runner, stores result. (2) Cache hit → returns without calling runner. (3) Different prompt hash → cache miss. (4) `clear()` removes files.

### Task B0.2: Pipeline-scoped scan cache

**Files:**
- Create: `ams/src/architecture_model/manifest/scan_cache.py`
- Modify: `ams/src/architecture_model/manifest/scanner.py` — add optional `cache` param to `scan_file()`
- Modify: `ams/src/architecture_model/manifest/generator.py` — create cache, pass through
- Test: `ams/tests/test_scan_cache.py`

**What:** `ScanCache` — dict keyed on `(absolute_path, content_hash)`. `scan_file` checks cache before parsing. `generate_manifest` creates one cache instance, passes it to all scan calls, preventing 2-4x redundant scanning.

**Interface:**
```python
class ScanCache:
    def __init__(self): ...
    def get(self, filepath: Path) -> ModuleInfo | None: ...
    def put(self, filepath: Path, module: ModuleInfo) -> None: ...
    @property
    def hits(self) -> int: ...
    @property
    def misses(self) -> int: ...
```

**Tests:** (1) Same file scanned twice → second is cache hit. (2) Modified file → cache miss. (3) `hits`/`misses` counters correct.

---

## WS-B: LLM Functional-Decomposition Audit (opencode-arch)

*Depends on WS-B0.*

### Task B1: Audit tool implementation

**Files:**
- Create: `oa/src/opencode_arch/mcp/tools/llm_audit.py`
- Create: `oa/src/opencode_arch/llm/prompts/__init__.py`
- Create: `oa/src/opencode_arch/llm/prompts/audit.py` (prompt templates)
- Test: `oa/tests/test_llm_audit.py`

**What:** `architect_llm_audit(repo_path, model_yaml)` — two-stage blind decomposition.

**Stage 1 prompt:** Provide source code + CONTEXT.md + README.md (no F-block info). Ask for functional grouping with rationale.

**Stage 2 prompt:** Provide Stage 1 output + tool's F-block assignments + modularity/conductance scores. Ask for reconciliation with specific evidence for disagreements.

**Output:** `.architecture-models/llm-audit.json` per the schema in discussion.md §5.

**Tests:** Mock OpencodeRunner. (1) Stage 1 produces grouping. (2) Stage 2 produces comparison with agreement_rate. (3) Cached → no runner call. (4) Output written to correct path.

### Task B2: Register MCP tool

**Files:**
- Modify: `oa/src/opencode_arch/mcp/server.py`

**What:** Add `architect_llm_audit` as tool #16 with flag-gated semantics (never auto-invoked).

---

## WS-C: Requirements Traceability (architecture-model-standard + opencode-arch)

*Depends on WS-B0.*

### Task C1: Requirement entity type + satisfies relationship

**Files:**
- Modify: `ams/src/architecture_model/core/types.py`
- Modify: `ams/src/architecture_model/core/parser.py` (parse requirements from YAML)
- Modify: `ams/src/architecture_model/core/validator.py` (validate requirement entities)
- Test: `ams/tests/test_requirements.py`

**What:** Add `Requirement` dataclass:
```python
@dataclass
class Requirement(BaseEntity):
    text: str
    source_doc: str
    source_anchor: str
    content_hash: str
```

Add `SATISFIES = "satisfies"` to `RelationType` enum.

Add `requirements: list[Requirement]` to `Entities` dataclass.

Update parser to handle `entities.requirements` in YAML. Update validator for requirement ID format `REQ-\d+`.

**Tests:** (1) Parse model YAML with requirements. (2) Validate satisfies relationship. (3) Reject bad requirement ID format. (4) Round-trip save/load.

### Task C2: Function addressability — `id` field on FunctionSignature

**Files:**
- Modify: `ams/src/architecture_model/core/types.py:387` (FunctionSignature)
- Modify: `ams/src/architecture_model/manifest/types.py:25` (FunctionInfo — add `id` field)
- Modify: `ams/src/architecture_model/manifest/scanner.py` — derive ID during scan
- Test: `ams/tests/test_function_id.py`

**What:** Add `id: str = ""` to `FunctionSignature` and `FunctionInfo`. Format: `{component_id}::{function_name}`. Derive at scan time using file→component mapping when available, otherwise `{module_path}::{function_name}`.

### Task C3: Deterministic requirement extraction (Tier 1)

**Files:**
- Create: `oa/src/opencode_arch/requirements/__init__.py`
- Create: `oa/src/opencode_arch/requirements/parser.py`
- Test: `oa/tests/test_req_parser.py`

**What:** Parse requirements docs with recognizable structure:
- `REQ-\d+` IDs → exact extraction
- `### Requirement:` headings → structured extraction
- Checkbox lists → item extraction

Returns `list[Requirement]` with `extraction_method: "structural"`, exact `source_anchor`.

### Task C4: LLM-assisted requirement extraction (Tier 2)

**Files:**
- Create: `oa/src/opencode_arch/requirements/llm_extractor.py`
- Create: `oa/src/opencode_arch/llm/prompts/requirements.py`
- Test: `oa/tests/test_req_llm.py`

**What:** For freeform prose docs: LLM segments into requirements with best-effort anchors. Tagged `extraction_method: "llm_segmented"`. Uses cached_llm_call from WS-B0.

### Task C5: Retroactive requirement derivation

**Files:**
- Create: `oa/src/opencode_arch/requirements/retroactive.py`
- Test: `oa/tests/test_req_retroactive.py`

**What:** For repos with no requirements doc: derive requirements from capability descriptions, behavior names, test assertions. Uses LLM to synthesize a requirements list from existing model artifacts. Tagged `extraction_method: "retroactive"`.

### Task C6: Function → Requirement matching (`satisfies` edges)

**Files:**
- Create: `oa/src/opencode_arch/requirements/matcher.py`
- Create: `oa/src/opencode_arch/llm/prompts/matching.py`
- Test: `oa/tests/test_req_matcher.py`

**What:** LLM matches functions to requirements using `body_hints`, `test_contracts`, and function names as evidence. Each match includes confidence + evidence string. Uses cached_llm_call.

### Task C7: MCP tool `architect_trace_requirements`

**Files:**
- Create: `oa/src/opencode_arch/mcp/tools/trace_requirements.py`
- Modify: `oa/src/opencode_arch/mcp/server.py`
- Test: `oa/tests/test_trace_req_tool.py`

**What:** Tool #17. Takes `repo_path`, `model_yaml`, `requirements_doc` (optional — if absent, uses retroactive mode). Orchestrates C3→C4→C5→C6. Output: `.architecture-models/requirements-trace.json`. Purely additive.

### Task C8: Coverage dimension 8 — requirement traceability

**Files:**
- Modify: `ams/src/architecture_model/core/coverage.py`
- Test: extend coverage tests

**What:** Add `_check_requirement_traceability(model) -> CoverageCheck`. Reports orphan functions, orphan requirements, low-confidence coverage. Returns `null`/`not_run` when no requirements configured.

---

## WS-D: Fix Silent Pipeline Failures (opencode-arch)

### Task D1: Structured pipeline response

**Files:**
- Modify: `oa/src/opencode_arch/mcp/tools/extract.py`
- Test: `oa/tests/test_extract_pipeline.py`

**What:** Replace all bare `except Exception: pass` blocks (13 of them) with error-capturing blocks. Build a `pipeline` dict tracking each step's status:

```python
pipeline = {}
# Each step:
try:
    # ... step logic ...
    pipeline["docs"] = {"status": "ok", "files": [...]}
except Exception as e:
    pipeline["docs"] = {"status": "error", "error": str(e)}
```

Return `pipeline` dict in result. Return `warnings` list for non-fatal issues.

**Tests:** (1) Successful pipeline → all steps "ok". (2) Simulated doc failure → docs step shows "error", other steps still run. (3) Result always includes `pipeline` key.

### Task D2: Evaluate TOOL_WARNINGS in `@with_quality`

**Files:**
- Modify: `oa/src/opencode_arch/mcp/quality.py:105`
- Test: extend `oa/tests/test_quality.py`

**What:** After the wrapped function returns, evaluate the `TOOL_WARNINGS` rules against the result dict. Append any triggered warnings to `result["warnings"]`.

```python
# In with_quality, after func() returns:
tool_name = func.__name__  # or derive from module
if tool_name in TOOL_WARNINGS:
    for name, check_fn, message in TOOL_WARNINGS[tool_name]:
        if check_fn(result):
            warnings.append({"rule": name, "message": message})
```

**Tests:** (1) Warning rule triggers when condition met. (2) No warnings when conditions clear. (3) Warnings appear in result dict.

### Task D3: Model snapshots before overwrite

**Files:**
- Modify: `oa/src/opencode_arch/mcp/tools/extract.py` (before line 83 where model is written)
- Test: extend `oa/tests/test_extract_pipeline.py`

**What:** Before writing `.architecture-model.yaml`, if it already exists, copy to `.architecture/snapshots/{ISO-timestamp}.yaml`. Cap at 10 snapshots (delete oldest).

**Tests:** (1) First extraction → no snapshot (no prior model). (2) Second extraction → snapshot created. (3) 12 extractions → only 10 snapshots kept.

---

## WS-E: Close Interface Gap (architecture-model-standard + opencode-arch)

### Task E1: Auto-extract interfaces during extraction

**Files:**
- Modify: `oa/src/opencode_arch/mcp/tools/extract.py`
- Modify: `ams/src/architecture_model/orchestration/auto_enrich.py:443` (verify `extract_component_interfaces` works)
- Test: `oa/tests/test_interface_extraction.py`

**What:** After behaviors are created in the extract pipeline, call `extract_component_interfaces(model, source_graph)` where `source_graph` is built from the manifest's import data. This populates `model.entities.interfaces`, making the ICD doc generator produce useful output.

**Challenge:** `extract_component_interfaces` takes a `SourceGraph`, but the Python pipeline uses `Manifest`. Need a `manifest_to_source_graph(manifest) -> SourceGraph` adapter.

**Adapter location:** `ams/src/architecture_model/orchestration/auto_enrich.py` — add `manifest_to_source_graph()`.

**Tests:** (1) Extraction on repo with cross-component imports → interfaces populated. (2) ICD doc is non-empty after extraction.

---

## WS-F: New Doc Generators (architecture-model-standard + opencode-arch)

### Task F1: Rich component spec generator

**Files:**
- Modify: `ams/src/architecture_model/docs/component_spec.py`
- Test: `ams/tests/test_component_spec.py`

**What:** Rewrite to include: component overview, file list with function counts, internal relationships, external dependencies, behaviors realized, interface summary, confidence score.

### Task F2: System design document generator

**Files:**
- Create: `ams/src/architecture_model/docs/system_design.py`
- Test: `ams/tests/test_system_design.py`

**What:** `generate_system_design(model, manifest) -> str` — produces a top-level system design doc: architecture overview (from meta), layer structure, component inventory table, key behaviors, deployment constraints, Mermaid component diagram.

### Task F3: Integration flow generator

**Files:**
- Create: `ams/src/architecture_model/docs/integration_flows.py`
- Test: `ams/tests/test_integration_flows.py`

**What:** `generate_integration_flows(model) -> str` — for each cross-component relationship, generate a flow description with source/target component details, relationship type, and Mermaid flowchart.

### Task F4: Wire new generators into `architect_docs` tool

**Files:**
- Modify: `oa/src/opencode_arch/mcp/tools/docs.py`
- Test: extend `oa/tests/test_docs_tool.py`

**What:** Add `system_design`, `integration_flows` to the default doc set and as standalone format options.

---

## Execution Order (recommended)

**Phase 1 — All independent (parallel):**
- WS-A (Tasks A1-A5): F-block accuracy — ams only
- WS-B0 (Tasks B0.1-B0.2): LLM cache + scan cache — oa + ams
- WS-D (Tasks D1-D3): Silent failure fixes — oa only
- WS-E (Task E1): Interface gap — oa + ams
- WS-F (Tasks F1-F4): Doc generators — ams + oa

**Phase 2 — After WS-B0 (parallel):**
- WS-B (Tasks B1-B2): LLM audit — oa only
- WS-C (Tasks C1-C8): Requirements traceability — ams + oa

**Total: 27 tasks across 6 workstreams.**
