# Component: Tools (COMP-1)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
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

None

### Dependents (incoming)

None

## Behaviors Realized

None

## Public API

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `author_architecture` | `repo_path: str, requirements_text: str` | `dict[str, Any]` | Parse requirements text and produce a concept-phase architecture model.

Args:
    repo_path: Absolute path to the repository root.
    requirements_text: Free-form or structured requirements document text.

Returns:
    Dict with model_path, entity counts, and lifecycle_phase. |
| `check_representativeness` | `repo_path: str, model_yaml: str` | `dict[str, Any]` | Check how well an architecture model represents the actual codebase.

Supports three modes:
- Hierarchical (config): uses pre-existing source_block_dict from config
- Hierarchical (auto): generates F-blocks from module grouping when no config exists
- Flat: fallback when neither hierarchical path is available

Args:
    repo_path: Absolute path to the repository root.
    model_yaml: The architecture model YAML to evaluate.

Returns:
    Dict with scores, details, and suggested improvements. |
| `store_correction` | `repo_path: str, correction_type: str, target: str, reason: str, suggestion: dict | None` | `dict[str, Any]` | Store a structured correction for the architecture model.

Corrections are consumed on next pipeline run to improve the model.

Args:
    repo_path: Absolute path to the repository.
    correction_type: One of: split_component, merge_components, add_component,
        remove_component, add_relationship, remove_relationship, rename, reclassify.
    target: Entity ID being corrected (e.g., "COMP-3").
    reason: Why this correction is needed.
    suggestion: Optional structured suggestion (format depends on type). |
| `decompose_repository` | `repo_path: str` | `dict[str, Any]` | Decompose architecture model into per-block sub-models and recursive manifests.

Reads .architecture-model.yaml, traces relationships per F-block,
writes sub-models to .architecture-models/ and per-block manifests
to .architecture/manifests/.

Args:
    repo_path: Absolute path to the repository.

Returns:
    Dict with sub_models, recursive_manifests, and paths. |
| `generate_docs` | `repo_path: str, formats: str` | `dict[str, Any]` | Generate standard SE documentation from an architecture model.

Produces component specs, ICDs, dependency matrix, health report,
and index from .architecture-model.yaml.

Args:
    repo_path: Absolute path to the repository.
    formats: Comma-separated list of doc types to generate.
        Options: all, component_spec, icd, dependency_matrix, health, drift, index.
        Default: "all".

Returns:
    Dict with generated file paths and any errors. |
| `export_repository` | `repo_path: str, output_dir: str, output_format: str, prefix: str` | `dict[str, Any]` | Export repository architecture as flat files for mobile AI.

Builds a set of flat files (model, sub-models, docs, manifests, specs,
diagrams, skills, reference docs) suitable for use in token-limited
AI environments.

Args:
    repo_path: Absolute path to the repository.
    output_dir: Where to write output. Default: {repo_path}/.architecture-export/
    output_format: "dir" (flat directory) or "zip" (single zip file).
    prefix: File prefix override. Default: auto-derived from repo name.

Returns:
    Dict with file list, sizes, and output location. |
| `store_extraction` | `repo_path: str, model_yaml: str, context_tokens: int` | `dict[str, Any]` | Validate and store an architecture model extraction.

Called AFTER the agent has produced a YAML architecture model.
Validates the model, writes it to .architecture-model.yaml,
and records telemetry.

Args:
    repo_path: Path to the repository root (where to save the model).
    model_yaml: The YAML architecture model produced by the agent.
    context_tokens: How many tokens of context the agent used (for telemetry).

Returns:
    Dict with: stored (bool), score (int), issues (list), telemetry_recorded (bool),
    pipeline (dict), warnings (list). |
| `record_feedback` | `repo_path: str, feedback_type: str, content: str, context: dict | None, rating: int | None, correction: dict | None` | `dict[str, Any]` | Record user feedback to .architecture/feedback.jsonl.

Args:
    repo_path: Repository root path
    feedback_type: "correction" | "rating" | "tool_feedback" | "training"
    content: The feedback content (human-readable)
    context: Optional context dict (tool name, prompt, response, etc.)
    rating: Optional 1-5 quality rating
    correction: Optional structured correction {entity_id, field, old, new}

Returns:
    {recorded, feedback_id, total_feedback} |
| `check_gate` | `repo_path: str, model_yaml: str` | `dict[str, Any]` | Check development gate for an architecture model against code reality.

Args:
    repo_path: Absolute path to the repository root.
    model_yaml: Optional YAML string. If empty, reads .architecture-model.yaml.

Returns:
    Dict with lifecycle_phase, sub-scores, phase_requirements_met, and issues. |
| `run_tests_on_generated_code` | `repo_path: str, test_command: str | None` | `dict[str, Any]` | Run the repository's test suite against generated code.

This is the quality gate for code generation. The agent generates code,
then calls this tool to verify it passes the original tests.

Args:
    repo_path: Path to the repository with generated code + tests.
    test_command: Custom test command. Defaults to pytest.

Returns:
    Dict with: passed (bool), pass_rate (float), total_tests (int),
    passed_tests (int), failures (list of failure descriptions). |
| `group_repository` | `repo_path: str, target_groups: int` | `dict[str, Any]` | Group repository modules into logical architecture components.

Uses multi-signal affinity (subdirectory, name-prefix, imports) to
cluster source files into coherent component groups. This provides
suggested component boundaries for architecture extraction.

Args:
    repo_path: Absolute path to the repository root.
    target_groups: Desired number of groups. 0 = auto-calculate.

Returns:
    Dict with keys: groups, total_modules, total_groups, filtered_trivial.
    Each group has: name, files, file_count, locked.
    Returns {"error": "..."} on failure. |
| `ingest_source_graph` | `repo_path: str, source_graph_json: str` | `dict` | Ingest a SourceGraph JSON and generate architecture components.

Args:
    repo_path: Absolute path to the repository.
    source_graph_json: JSON string with SourceGraph data.

Returns:
    Dict with components, interfaces, and group info. |
| `run_llm_audit` | `repo_path: str, model_yaml: str, _runner, _cache: LLMCache | None` | `dict[str, Any]` | Run two-stage LLM functional-decomposition audit. |
| `regen_score` | `repo_path: str, component_id: str` | `dict` | Compute regen readiness score for a repository or specific component.

Returns overall score, grade, per-component breakdown, and blockers. |
| `spot_check` | `repo_path: str, component_id: str, subsystem_id: str` | `dict` | Run a spot-check regeneration probe on a component or subsystem.

Regenerates code via LLM, compares against source, reports diagnostics.
On failure, classifies patterns and suggests healing actions. |
| `capture_requirement` | `repo_path: str, requirement: str, component_id: str | None, priority: str, context: str` | `dict[str, Any]` | Store a functional requirement linked to a component.

Args:
    repo_path: Repository root path
    requirement: The requirement text
    component_id: Component ID (e.g., "COMP-3"). If None, stored as unlinked.
    priority: must | should | could (MoSCoW)
    context: Additional context from conversation

Returns:
    {stored, requirement_id, component, total_requirements} |
| `scan_repository` | `repo_path: str` | `dict[str, Any]` | Scan a repository and generate its reality manifest.

Performs AST analysis on all source files to produce a ground-truth
inventory of modules, functions, classes, imports, and metrics.

Args:
    repo_path: Absolute path to the repository root.

Returns:
    Manifest dict with keys: generated_at, project_root, metrics,
    functional_blocks, modules, interfaces.
    Returns {"error": "..."} on failure. |
| `compute_adaptive_budget` | `module_count: int, base: int` | `int` | Scale token budget with repository size.

Small repos (<=20 modules): base budget (4000 tokens)
Medium repos: +200 tokens per 10 modules over 20
Large repos: capped at 16000 tokens

Examples:
    20 modules → 4000 tokens
    50 modules → 4600 tokens  
    100 modules → 5600 tokens
    161 modules → 6800 tokens
    500 modules → 16000 tokens (capped) |
| `slice_context` | `repo_path: str, focus: str, budget: int, detail: str` | `str` | Generate an optimized context slice from a repository.

This is the core token-arbitrage function. It compresses a full repository
into a dense, structured context string within the token budget.

If an .architecture-model.yaml exists, uses the model + slicer + formatter.
Otherwise, falls back to manifest-based context.

Args:
    repo_path: Absolute path to the repository root.
    focus: Focus scope - "all", an source-block ID (e.g. "F1"), a layer name,
           or an artifact name (e.g. "icd", "requirements-analysis").
    budget: Maximum token budget (1 token ~ 4 chars).
    detail: Detail level - "minimal", "standard", or "full".

Returns:
    Formatted context string within budget, or error message. |
| `get_stats` | `repo_path: str, tool_filter: str` | `dict[str, Any]` | Aggregate quality and performance metrics.

Returns session stats, historical telemetry summary, and actionable suggestions.

Args:
    repo_path: Optional - filter stats to specific repo.
    tool_filter: Optional - filter to specific tool name. |
| `trace_requirements` | `repo_path: str, model_yaml: str, requirements_doc: str, _runner, _cache` | `dict` | Trace requirements to functions.

If requirements_doc provided: parse structurally, fall back to LLM for freeform.
If no requirements_doc: use retroactive derivation from model.
Then match functions to requirements.
Output: .architecture-models/requirements-trace.json |
| `validate_architecture` | `model_yaml: str` | `dict[str, Any]` | Validate an architecture model for structural correctness.

Args:
    model_yaml: The YAML architecture model string to validate.

Returns:
    Dict with: score (0-100), issues (list), entity_count, relationship_count, is_valid. |

## Interface Dependencies

- **provides** `exposes_to_Cli` → COMP-3 (Cli) [store_extraction]
- **requires** `uses_Resolution` → COMP-5 (Resolution) [estimate_regenerability, check_fidelity, with_quality, SessionAccumulator]
- **requires** `uses_Cli` → COMP-3 (Cli) [drain_and_store]
- **requires** `uses_Requirements` → COMP-4 (Requirements) [hash_content, cached_llm_call, CachedResult, LLMCache]

## Patterns

None

## Confidence

65%
