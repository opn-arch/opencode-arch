# Component: Cli (COMP-3)

**Status:** Status.ACTIVE
**Description:** —

## Files

| File | Functions | Classes |
|------|-----------|---------|
| `src/opencode_arch/cli/bench.py` | — | — |
| `src/opencode_arch/cli/calibrate.py` | — | — |
| `src/opencode_arch/cli/confidence.py` | — | — |
| `src/opencode_arch/cli/docs.py` | — | — |
| `src/opencode_arch/cli/docs_validator.py` | — | — |
| `src/opencode_arch/cli/export_data.py` | — | — |
| `src/opencode_arch/cli/extract.py` | — | — |
| `src/opencode_arch/cli/gap_analyzer.py` | — | — |
| `src/opencode_arch/cli/generate.py` | — | — |
| `src/opencode_arch/cli/launch.py` | — | — |
| `src/opencode_arch/cli/main.py` | — | — |
| `src/opencode_arch/cli/metrics.py` | — | — |
| `src/opencode_arch/cli/regen_loop.py` | — | — |
| `src/opencode_arch/runner/base.py` | — | — |
| `src/opencode_arch/runner/opencode.py` | — | — |
| `src/opencode_arch/telemetry/collector.py` | — | — |
| `src/opencode_arch/telemetry/recorder.py` | — | — |
| `src/opencode_arch/telemetry/store.py` | — | — |
| `src/opencode_arch/learning/adapter.py` | — | — |
| `src/opencode_arch/learning/assessor.py` | — | — |
| `src/opencode_arch/learning/classifier.py` | — | — |
| `src/opencode_arch/learning/lessons.py` | — | — |
| `src/opencode_arch/learning/maintainer.py` | — | — |
| `src/opencode_arch/learning/patterns.py` | — | — |

## Responsibilities

- is valid
- run
- run
- record
- query
- averages
- log regen outcome
- get patterns
- query regen outcomes
- record learning curve
- get learning curve
- record report card
- get report cards
- record lesson
- get lessons
- mark lesson applied
- record drift flag
- get drift flags
- resolve drift flag
- record function metric
- get function metrics

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
| `run_bench` | `repos: list[str], runner: RunnerBackend, budget: int, target_score: int` | `list[dict[str, Any]]` | Run extraction benchmark on multiple repositories. |
| `select_calibration_targets` | `model_or_components, n: int, min_confidence: float, count: int` | `` | Select components for calibration.

Supports two calling conventions:
- Legacy: select_calibration_targets(model, n=3, min_confidence=0.7) with ArchitectureModel
- New: select_calibration_targets(components, count=6) with list[dict] |
| `format_calibration_prompt` | `comp: Component` | `str` | Format a prompt asking the agent to regenerate a component from its model spec. |
| `compare_regeneration` | `original: 'str | Path', generated: str` | `dict` | Compare original and generated source code by public API coverage.

original can be a string of source code or a Path to a file. |
| `format_regeneration_prompt` | `component_context: dict` | `str` | Format a prompt for regenerating a component from model data only. |
| `compute_correlation` | `data: list[dict]` | `float` | Pearson correlation between confidence and regen_quality fields. |
| `run_confidence` | `repo_path: str` | `str` | Run confidence analysis and return formatted output. |
| `run_docs_generate` | `repo_path: Path, runner: RunnerBackend, output_dir: Path | None, artifact_filter: list[str] | None, model_path: Path | None` | `DocsResult` | Generate SE documentation for a project.

Flow:
1. Load model from project (or model_path override)
2. Generate manifest via generate_manifest()
3. Call select_artifacts(model, manifest) to determine what to generate
4. If artifact_filter provided, intersect with selected artifacts
5. For each artifact:
   a. Get template from TEMPLATES[artifact_id]
   b. Assemble context via assemble_artifact_context(template, model, manifest)
   c. Build full prompt (context + generation instructions)
   d. Call runner.run(prompt, str(repo_path))
   e. Write result to output_dir/filename
6. Generate index.md linking all artifacts
7. Return DocsResult |
| `run_docs_list` | `repo_path: Path, model_path: Path | None` | `list[dict[str, str]]` | List which artifacts would be generated for a project.

Returns list of dicts: [{"id": ..., "name": ..., "category": ..., "priority": ...}]
No runner needed — just model analysis. |
| `validate_docs` | `docs_dir: Path, model: 'ArchitectureModel', manifest: dict | None` | `DocsValidationResult` | Validate all markdown files in docs_dir against model and manifest.

Checks:
1. File paths mentioned in docs exist in manifest's file inventory
2. Function/class names referenced exist in manifest's AST data
3. Component IDs/names referenced match model's components
4. Interface names referenced match model's interfaces

An artifact PASSES if it has no "error" severity issues. |
| `is_valid` | `` | `bool` | No errors (warnings are OK). |
| `run_export_data` | `...` | `` |  |
| `run_extract` | `repo_path: str, runner: RunnerBackend, budget: int, focus: str, target_score: int` | `dict[str, Any]` | Run the full extraction loop.

1. Validates repo exists
2. Calls runner with extraction prompt
3. Parses YAML from output
4. Validates and stores via tool APIs
5. Returns metrics |
| `analyze_gaps` | `test_output: str, model_context: str` | `str` | Parse test failure output and produce enrichment feedback.

Maps common failure patterns to structured feedback for the next
iteration prompt. Returns a formatted string summarizing what needs
fixing.

Args:
    test_output: Raw pytest output (stdout + stderr).
    model_context: Optional architecture model context for cross-referencing.

Returns:
    Formatted feedback string with identified gaps. |
| `run_generate` | `repo_path: str, runner: RunnerBackend, max_iter: int, test_command: str | None` | `dict[str, Any]` | Run the test-guided code generation loop. |
| `run_launch` | `repo_path: str | None, skip_exec: bool` | `dict` | Run pre-flight checks and launch interactive OpenCode session.

Args:
    repo_path: Target repository (default: current directory)
    skip_exec: If True, do pre-flight only without exec (for testing)

Returns:
    Pre-flight results dict (only if skip_exec=True) |
| `main` | `` | `` |  |
| `show_metrics` | `tool: str | None, last: int, learning_curve: bool, drift: bool` | `` | Query and display metrics from the telemetry store. |
| `show_report` | `repo: str | None, last: int` | `` | Display report cards from telemetry. |
| `format_metrics_table` | `records: list[dict]` | `str` | Format records as a readable table. |
| `run_subsystem_tests` | `test_files: list[Path], repo_path: Path` | `dict[str, Any]` | Run pytest on specific test files and return structured results.

Args:
    test_files: List of test file paths to run.
    repo_path: Root path of the repository (used as cwd).

Returns:
    {"passed": int, "failed": int, "total": int, "pass_rate": float, "output": str} |
| `run_regen_loop` | `repo_path: Path, runner: RunnerBackend, max_iterations: int, target_pass_rate: float, subsystem_name: str | None, blind: bool` | `dict[str, Any]` | Run the test-as-oracle decomposed regen loop.

Decomposes the repo into subsystems by test affinity, then iteratively
regenerates code per subsystem using the LLM, running tests after each
attempt to measure convergence.

Args:
    repo_path: Path to the target repository.
    runner: RunnerBackend for LLM invocation.
    max_iterations: Max iterations per subsystem (default 5).
    target_pass_rate: Stop when this pass rate is achieved (default 0.5).
    subsystem_name: If set, only process this subsystem.
    blind: If True, agent works in temp dir without source file access.

Returns:
    Summary dict with per-subsystem results and overall metrics. |
| `run` | `prompt: str, repo_path: str` | `RunResult` | Run the agent with a prompt in a repo context. |
| `run` | `prompt: str, repo_path: str` | `RunResult` | Run OpenCode with a prompt in the given repo directory.

Uses stdin to pass the prompt (avoids ARG_MAX limits for long prompts).
Uses cwd to set the working directory (no --dir flag needed). |
| `drain_and_store` | `tool: str, repo: str, db_path: str | None` | `int` | Drain the thread-local metrics collector and write to telemetry DB.

Returns the number of metrics stored. Never raises — swallows all exceptions. |
| `record_invocation` | `store: TelemetryStore, tool: str, repo: str, context_tokens: int, output_quality: int, iterations: int, metadata: str` | `` | Record a tool invocation asynchronously. |
| `record` | `tool: str, repo: str, context_tokens: int, output_quality: int, iterations: int, metadata: str` | `` |  |
| `query` | `tool: str | None, limit: int` | `list[dict[str, Any]]` |  |
| `averages` | `tool: str` | `dict[str, float]` |  |
| `log_regen_outcome` | `repo: str, subsystem: str, iteration: int, features: dict[str, int], pass_rate: float, time_seconds: float, prompt_tokens: int, source_equivalent_tokens: int, compression_ratio: float, mode: str` | `` | Log a regeneration attempt outcome.

Args:
    repo: Repository name.
    subsystem: Subsystem name.
    iteration: Which iteration converged (or max if didn't).
    features: Dict with constant_count, signature_count, contract_count.
    pass_rate: Final pass rate achieved.
    time_seconds: Wall-clock time for this subsystem.
    prompt_tokens: Tokens used in the prompt.
    source_equivalent_tokens: Tokens agent would need without extension.
    compression_ratio: source_equivalent / prompt_tokens.
    mode: Regen mode ('normal' or 'blind'). |
| `get_patterns` | `repo_category: str | None` | `list[dict[str, Any]]` | Retrieve learned patterns from regen outcomes.

Returns aggregated stats per subsystem showing average pass rates,
iteration counts, and feature correlations.

Args:
    repo_category: Optional filter by repo name pattern.

Returns:
    List of dicts with pattern information. |
| `query_regen_outcomes` | `repo: str | None, limit: int` | `list[dict[str, Any]]` | Query raw regen outcome records.

Args:
    repo: Optional filter by repo name.
    limit: Max records to return.

Returns:
    List of outcome records as dicts. |
| `record_learning_curve` | `repo: str, mode: str, total_subsystems: int, converged_subsystems: int, avg_pass_rate: float, avg_iterations: float, avg_prompt_tokens: float, avg_source_equivalent: float, avg_compression_ratio: float, total_time_seconds: float` | `` | Record per-repo summary for learning curve trend analysis.

repo_sequence is auto-computed as the count of previous entries + 1.
This allows tracking: does the system get better with each new repo? |
| `get_learning_curve` | `mode: str | None` | `list[dict[str, Any]]` | Get learning curve data ordered by repo sequence.

Shows how metrics improve with each successive repo processed.
Key metrics that should IMPROVE (go down):
- avg_iterations: fewer attempts needed
- avg_prompt_tokens: more efficient prompts

Key metrics that should IMPROVE (go up):
- avg_pass_rate: higher fidelity
- avg_compression_ratio: better token arbitrage
- converged_subsystems / total_subsystems: higher success rate |
| `record_report_card` | `repo: str, mode: str, grade: str, fidelity: float, compression_ratio: float, failure_patterns: str, novel_patterns: int, improvement_actions: str` | `` | Record a report card for a repo run. |
| `get_report_cards` | `repo: str | None, limit: int` | `list[dict[str, Any]]` | Query report cards, optionally filtered by repo. |
| `record_lesson` | `lesson_id: str, discovered_repo: str, category: str, description: str, evidence: str` | `` | Record a new lesson learned. Ignores duplicates (same lesson_id). |
| `get_lessons` | `category: str | None` | `list[dict[str, Any]]` | Query all lessons, optionally filtered by category. |
| `mark_lesson_applied` | `lesson_id: str, repo: str` | `` | Mark a lesson as applied to a specific repo. |
| `record_drift_flag` | `file: str, issue: str, severity: str, auto_fixable: bool, suggested_fix: str` | `` | Record a documentation drift flag. |
| `get_drift_flags` | `resolved: bool` | `list[dict[str, Any]]` | Get drift flags, optionally filtered by resolution status. |
| `resolve_drift_flag` | `flag_id: int` | `` | Mark a drift flag as resolved. |
| `record_function_metric` | `tool: str, function: str, module: str, repo: str, time_ms: float, quality_scores: str, input_metrics: str, output_metrics: str` | `None` | Record a function-level metric. |
| `get_function_metrics` | `repo: str, function: str, tool: str, last: int` | `list[dict]` | Query function metrics with optional filters. |
| `get_adaptations` | `subsystem_name: str, dependency_count: int, signature_count: int, contract_count: int, body_hint_coverage: float, historical_patterns: list[dict[str, Any]] | None` | `list[PromptAdaptation]` | Determine prompt adaptations based on subsystem characteristics and history.

This is called BEFORE the first prompt attempt to proactively adjust
based on what we've learned from previous repos.

Args:
    subsystem_name: Name of the current subsystem.
    dependency_count: Number of upstream dependencies.
    signature_count: Number of function signatures in model.
    contract_count: Number of test contracts available.
    body_hint_coverage: Fraction of functions with body_hints (0.0-1.0).
    historical_patterns: Past failure patterns from telemetry for similar subsystems.

Returns:
    List of adaptations to apply to prompt construction. |
| `apply_adaptations` | `adaptations: list[PromptAdaptation], contract_cap: int, include_dep_body_hints: bool` | `dict[str, Any]` | Apply adaptations and return modified prompt parameters.

Returns a dict of overrides to pass to _build_prompt:
- contract_cap: int (max contracts to include)
- include_dep_body_hints: bool (include body_hints in dep context)
- extra_context: str (additional context to append)
- source_excerpts: list[str] (functions needing full source) |
| `generate_report_card` | `repo: str, mode: str, subsystem_results: dict[str, dict[str, Any]], previous_fidelity: float | None, previous_compression: float | None` | `ReportCard` | Generate a report card from regen loop results.

Args:
    repo: Repository name.
    mode: "normal" or "blind".
    subsystem_results: Dict of {subsystem_name: result_dict} from run_regen_loop.
    previous_fidelity: Fidelity from previous repo (for trend).
    previous_compression: Compression from previous repo (for trend).

Returns:
    ReportCard with grade, trends, and improvement actions. |
| `classify_failures` | `test_output: str, pass_rate: float, total_tests: int, failed_tests: int` | `list[FailureClassification]` | Classify test failures using both raw and structured analysis.

Args:
    test_output: Raw pytest stdout/stderr text.
    pass_rate: Overall pass rate (0.0-1.0).
    total_tests: Total number of tests run.
    failed_tests: Number of failed tests.

Returns:
    List of classified failures, sorted by confidence (highest first). |
| `extract_lessons` | `repo: str, mode: str, subsystem_results: dict[str, dict[str, Any]]` | `list[Lesson]` | Extract lessons from a completed regen loop run.

Looks for:
- Correlation between features and convergence
- Novel patterns not in taxonomy
- Success patterns worth replicating
- Limitations to document

Args:
    repo: Repository name.
    mode: "normal" or "blind".
    subsystem_results: Results from run_regen_loop.

Returns:
    List of lessons extracted. |
| `detect_drift` | `project_root: Path` | `list[DriftFlag]` | Run all drift detection checks on a project.

Args:
    project_root: Path to the project to check.

Returns:
    List of detected drift issues (may be empty if all is well). |
| `auto_fix_drift` | `flags: list[DriftFlag], project_root: Path` | `list[DriftFlag]` | Auto-fix drift flags that are marked as auto_fixable.

Args:
    flags: List of detected drift flags.
    project_root: Path to the project root.

Returns:
    List of flags that were successfully fixed. |

## Interface Dependencies

- **requires** `uses_Tools` → COMP-1 (Tools) [store_extraction]
- **provides** `exposes_to_Tools` → COMP-1 (Tools) [drain_and_store]

## Patterns

- monitor

## Confidence

100%
