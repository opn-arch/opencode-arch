# Component: Resolution (COMP-5)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/regen/self_heal.py` | — | — |
| `src/opencode_arch/regen/spot_check.py` | — | — |
| `src/opencode_arch/agent/resolution.py` | — | — |
| `src/opencode_arch/mcp/quality.py` | — | — |
| `src/opencode_arch/context/formatter.py` | — | — |
| `src/opencode_arch/context/pipeline_bridge.py` | — | — |

## Responsibilities

- register handler
- resolve
- resolve all
- unresolvable categories
- record
- summary

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
| `classify_failure` | `diagnostics: list[SpotCheckDiagnostic]` | `list[HealAction]` | Classify failure diagnostics into actionable heal actions. |
| `self_heal` | `result: SpotCheckResult, repo_path: Path, learning_store: Any` | `list[HealAction]` | Analyze a failed spot-check and produce healing actions.

Records outcomes in learning store for cross-session improvement. |
| `select_target` | `repo_path: Path, component_id: str | None, subsystem_id: str | None` | `SpotCheckTarget` | Select and prepare a spot-check target.

If component_id specified, use that.
If subsystem_id specified, load that subsystem's model.
If neither, pick the easiest (highest static score, smallest). |
| `run_spot_check` | `target: SpotCheckTarget, repo_path: Path, max_iterations: int, llm_backend: Any` | `SpotCheckResult` | Run the spot-check: regen target via LLM, diff against source, iterate on failure.

If llm_backend is None, returns a dry-run result showing what WOULD be checked. |
| `register_handler` | `method: str, handler: Callable` | `None` | Register a resolution handler for a method type.

Handler signature: (uncertainty: Uncertainty) -> Evidence | None |
| `resolve` | `uncertainty: Uncertainty` | `ResolutionOutcome | None` | Attempt to resolve an uncertainty.

Returns ResolutionOutcome if resolved, None if unresolvable. |
| `resolve_all` | `uncertainties: list[Uncertainty]` | `list[ResolutionOutcome]` | Resolve a batch of uncertainties. Returns successful resolutions. |
| `unresolvable_categories` | `` | `set[str]` | Categories that have no handler registered. |
| `estimate_regenerability` | `compression_ratio: float, confidence: float, n_components: int, n_contracts: int` | `float` | Estimate regenerability based on compression ratio, confidence, components, and contracts. |
| `check_fidelity` | `input_data: Any, output_data: Any` | `dict` | Count entities in input vs output and detect data loss. |
| `with_quality` | `func` | `` | Decorator that appends _quality metadata to dict results. |
| `record` | `tool_name: str, latency_ms: float, warnings: list` | `` |  |
| `summary` | `` | `dict` |  |
| `format_model_context` | `model: ArchitectureModel, max_tokens: int, detail_level: str` | `str` | Format the full model as compact LLM context.

Args:
    model: Architecture model to format.
    max_tokens: Approximate token budget (1 token ~ 4 chars).
    detail_level: "minimal", "standard", or "full".

Returns:
    Formatted text suitable for LLM system prompt injection. |
| `format_source_block_context` | `model: ArchitectureModel, source_block: str, max_tokens: int, project_root: 'Path | None'` | `str` | Format context for a single F-block (for artifact section regeneration).

Produces: capability description, related UCs, components, interfaces.
If *project_root* is given, sub-models are auto-loaded for richer detail,
and per-block manifests are consumed for function-level context. |
| `format_artifact_context` | `model: ArchitectureModel, artifact_name: str, max_tokens: int` | `str` | Format context appropriate for regenerating a specific artifact.

Uses artifact-specific slicing then formats at appropriate detail level. |
| `query_model` | `model: ArchitectureModel, question: str` | `str` | Answer a structural question from model data.

Supports questions like:
- "What realizes F3?" → list behaviors with tag F3
- "What does UC-14 depend on?" → follow depends-on relationships
- "What interfaces does F4 expose?" → filter interfaces by provider |
| `impact_analysis` | `model: ArchitectureModel, entity_id: str, depth: int` | `str` | Determine what entities are affected if a given entity changes.

Traces relationships transitively up to `depth` levels. |
| `get_model` | `project_root: str | Path, force_refresh: bool` | `ArchitectureModel` | Load or generate the architecture model for the project.

If the model YAML exists and isn't stale, loads it.
If missing or force_refresh=True, re-extracts from artifacts and merges manifest.

Args:
    project_root: Path to project root directory.
    force_refresh: Force re-extraction even if model exists.

Returns:
    Loaded and validated ArchitectureModel. |
| `get_artifact_context` | `project_root: str | Path, artifact_name: str, max_tokens: int` | `str` | Get model-based context for artifact generation/regeneration.

This REPLACES the raw manifest slice with structured architectural context.
The returned string is injected into the LLM system prompt alongside the
manifest metrics (which are kept for ground-truth file counts).

Args:
    project_root: Project root path.
    artifact_name: Which artifact needs context.
    max_tokens: Token budget for the context block.

Returns:
    Formatted model context string for LLM prompt injection. |
| `get_source_block_context` | `project_root: str | Path, source_block: str, max_tokens: int` | `str` | Get model-based context for a single F-block (for section regeneration).

Args:
    project_root: Project root path.
    source_block: F-block ID (e.g., "S3").
    max_tokens: Token budget.

Returns:
    Formatted F-block context string. |
| `get_model_summary` | `project_root: str | Path` | `dict[str, Any]` | Get a summary dict of the model for injection into pipeline metadata.

Returns dict with entity_count, relationship_count, validation score, etc. |
| `enrich_manifest_slice` | `manifest_slice: str, project_root: str | Path, artifact_name: str, max_model_tokens: int` | `str` | Enrich an existing manifest slice with architecture model context.

This is the BACKWARD-COMPATIBLE integration point. The existing pipeline
generates manifest slices via _pipeline_manifest.py — this function
prepends model context to that slice, giving the LLM both:
1. Architectural structure (from model) — WHAT things mean, how they relate
2. Code-grounded metrics (from manifest) — WHAT actually exists

Args:
    manifest_slice: Raw manifest slice text (from _pipeline_manifest.py).
    project_root: Project root path.
    artifact_name: Which artifact this slice is for.
    max_model_tokens: Token budget for model context portion.

Returns:
    Combined context: model context + separator + manifest metrics. |

## Interface Dependencies

- **provides** `exposes_to_Tools` → COMP-1 (Tools) [estimate_regenerability, check_fidelity, with_quality, SessionAccumulator]

## Patterns

None

## Confidence

85%
