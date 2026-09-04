# MCP Architecture Lifecycle — Phase 2 (opencode-arch)

**Depends on:** `architecture-model-standard` branch `feat/curated-se-views` HEAD `7f0c7dc` (Phase 1 complete, 22 tasks, 2885 tests).
**Worktree:** `/Users/baigm2/Documents/Projects/opencode-arch/.worktrees/phase2-lifecycle` on branch `feat/phase2-lifecycle`.
**Base:** `main` at `174178d` (fix(check): evaluate referenced submodels).
**Baseline tests:** 452 passed, 2 pre-existing failures (`test_adaptive_budget.test_very_large_repo_capped`, `test_ingest.test_ingest_basic`).

## Environment

- Python: `/opt/anaconda3/bin/python`
- PYTHONPATH prefix (every test invocation): `PYTHONPATH="$PWD/src:/Users/baigm2/Documents/Projects/architecture-model-standard/.worktrees/curated-se-views/src"`
- Test command: `PYTHONPATH=... /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/e2e`
- Do NOT `pip install -e` anything (breaks fastmcp import per CONTEXT.md warning).
- Do NOT touch: `.architecture/*`, `.architecture-models/*`, `.architecture-model.yaml` (telemetry — leave dirty, never stage).
- Do NOT modify existing tool modules under `src/opencode_arch/mcp/tools/` except when the plan says so.
- One commit per task, Conventional Commit style. No `git add -A`.

## Scope

Register thin MCP endpoints wrapping every `architecture_model.lifecycle.*` and `architecture_model.ai.*` capability produced in Phase 1, plus the executors that Phase 1 deliberately deferred: rebuild runner, proposal apply, three-way merge, federated registry resolver, CLI wiring, and end-to-end integration tests.

**Design principles:**
1. MCP tool modules are thin adapters — one file per endpoint under `src/opencode_arch/mcp/tools/lifecycle/` or `src/opencode_arch/mcp/tools/ai/`. Each imports from `architecture_model.lifecycle.*` / `architecture_model.ai.*` and does path resolution + JSON marshaling only.
2. Every endpoint returns a JSON-serializable `dict`. Errors are structured `{ok: False, error: {code, message, details}}`; success is `{ok: True, ...}`. No exceptions escape MCP tool boundary.
3. Executors (rebuild, apply, merge) live under `src/opencode_arch/lifecycle_exec/` — a new package. They own the "run something" logic Phase 1 refused to specify.
4. Registry with existing skills: append entries to `src/opencode_arch/mcp/server.py`; do not rename or reorder existing tools.
5. Tests-first for every task. Full suite must remain green (baseline = 2 pre-existing failures unchanged).

## Task list

### Group A — foundational adapters (T1-T3)

#### T1: PhaseOne dependency + import surface

**Files:**
- Create `src/opencode_arch/lifecycle_bridge/__init__.py` — re-exports the Phase 1 public surface used by MCP tools.
- Create `tests/lifecycle_bridge/test_imports.py`.

**Spec:**
- `lifecycle_bridge` exposes: `PackageDescriptor`, `PackageLoader`, `AtomicStore`, `Journal`, `ModelSlice`, `ModelSliceMaterializer`, `ViewSpec`, `ArtifactSpec`, `ArtifactDAG`, `WorkOrder`, `Proposal`, `PROPOSAL_TYPES`, `proposal_from_dict`, `Job`, `JobState`, `JobStore`, `InvalidTransitionError`, `validate as validate_proposal`, `ValidationReport`.
- Test file imports each symbol and asserts non-None.
- Fail-early error message if the AM-standard worktree is not on `PYTHONPATH` — module top does `import architecture_model.lifecycle as _l` and raises a helpful `ImportError` if `_l.SchemaVersions.WORK_ORDER != "1.0.0"`.

**Commit:** `feat(bridge): expose Phase 1 lifecycle+AI surface for MCP tools`

---

#### T2: JSON error envelope + path resolver

**Files:**
- Create `src/opencode_arch/mcp/envelope.py`
- Create `tests/mcp/test_envelope.py`

**Spec:**
- `ok(data: dict) -> dict` returns `{"ok": True, **data}`.
- `err(code: str, message: str, **details) -> dict` returns `{"ok": False, "error": {"code", "message", "details"}}`.
- `resolve_repo(repo_path: str) -> Path` — validates path exists, is directory, returns absolute Path. Raises `ValueError` on unknown path (caught by tool wrappers).
- Standard error codes: `NOT_FOUND`, `INVALID_ARGUMENT`, `SCHEMA_VIOLATION`, `PRECONDITION_FAILED`, `INTERNAL`, `PHASE1_MISMATCH`.
- Decorator `@tool_result` wraps an async function so that raised exceptions become `err(INTERNAL, ...)` envelopes.

**Commit:** `feat(mcp): add result envelope and path resolver`

---

#### T3: Repository package root discovery

**Files:**
- Create `src/opencode_arch/lifecycle_exec/paths.py`
- Create `tests/lifecycle_exec/test_paths.py`

**Spec:**
- `package_root(repo_path: Path) -> Path` — locates `.architecture/` for lifecycle artifacts; creates `.architecture/lifecycle/` on first use.
- `package_index_path(repo_path) -> Path` returns `.architecture/lifecycle/index.yaml`.
- `slice_dir(repo_path) -> Path` returns `.architecture/lifecycle/slices/`.
- `view_dir`, `artifact_dir`, `workorder_dir`, `job_dir`, `journal_path` — analogous.
- All accessors idempotent; directory creation atomic.

**Commit:** `feat(lifecycle_exec): add repository path resolver`

---

### Group B — package endpoints (T4-T7)

#### T4: `architect_package_publish`

**Files:**
- Create `src/opencode_arch/mcp/tools/lifecycle/package_publish.py`
- Update `src/opencode_arch/mcp/server.py` (append registration; do not reorder existing tools).
- Create `tests/mcp/tools/lifecycle/test_package_publish.py`

**Spec:**
- Signature: `architect_package_publish(repo_path, model_yaml, manifest_json=None, parent_package_id=None) -> dict`.
- Wraps `architecture_model.lifecycle.publication.publish_package`.
- Success returns `{ok: True, package_id, revision, digest, index_path}`.
- Failure returns envelope-form errors for schema violation, digest mismatch, orphan package, cycle.
- Writes journal event via `Journal.record("package.publish", ...)`.

**Commit:** `feat(mcp): add architect_package_publish tool`

---

#### T5: `architect_package_load` + `architect_package_list_generations`

**AMENDED 2026-09-03 after T4 discovery.** Phase 1 exposes `list_generations(pkg) -> list[int]`, `read_current_generation(pkg) -> int|None`, but NO public `read_generation(pkg, n)` reader — the generation directory at `<pkg.root>/generations/<7-digit>/` contains model + manifest files that the tool reads directly.

**Files:**
- Create `src/opencode_arch/mcp/tools/lifecycle/package_load.py`
- Create `src/opencode_arch/mcp/tools/lifecycle/package_list_generations.py`
- Update server.py.
- Create `tests/mcp/tools/lifecycle/test_package_load.py`, `test_package_list_generations.py`.

**Spec:**
- `architect_package_load(repo_path, revision=None) -> {ok, package_id, revision, model_yaml, manifest_json, root_digest, generation_dir}`.
  - Loads the root `package.yaml` via `load_package(<repo>/.architecture/lifecycle/package.yaml)`.
  - If `revision=None`, calls `read_current_generation(pkg)`; if None returned → `err(NOT_FOUND, "no published generation")`.
  - If `revision` given, parses as `int(revision)` (7-digit form accepted); validates it exists in `list_generations(pkg)`.
  - Reads the generation dir directly: `<generation_dir>/architecture-model.yaml` and `<generation_dir>/manifest.json` (verify exact file names during implementation from `publish()` `bundle.files` dict keys).
  - `model_yaml` returned as string; `manifest_json` as string (or None if no manifest in bundle).
- `architect_package_list_generations(repo_path) -> {ok, package_id, current: str|None, generations: [str]}`.
  - `current` is the 7-digit string form of `read_current_generation` (or None).
  - `generations` is a list of 7-digit strings for all committed generations.

**Commit:** `feat(mcp): add package load and list-generations tools`

---

#### T6: `architect_package_diff`

**AMENDED.** Diff is computed between two generations of the same on-disk package (not between separate `package_id`s — there is only ONE root package per repo in Phase 1).

**Files:**
- Create `src/opencode_arch/mcp/tools/lifecycle/package_diff.py`
- Update server.py.
- Create `tests/mcp/tools/lifecycle/test_package_diff.py`

**Spec:**
- `architect_package_diff(repo_path, from_revision, to_revision) -> {ok, from_revision, to_revision, added, removed, changed}`.
- Loads the two generation models from `<pkg.root>/generations/<rev>/` directly, feeds both to `architecture_model.lifecycle.diff.semantic_diff`.
- Returns entity-level + relationship-level diff (all 17 relationship kinds).
- If `from_revision` or `to_revision` is not a committed generation → `err(NOT_FOUND, "generation not found", revision=...)`.

**Commit:** `feat(mcp): add semantic package diff tool`

---

#### T7: `architect_package_children_add` + `architect_package_stale`

**AMENDED (second revision).** Phase 1 discoveries corrected two spec errors:

1. `ArchitecturePackage.children` is `list[str]` — a list of **POSIX-relative paths** to child `package.yaml` files (e.g. `"subsystems/core/package.yaml"`), NOT dicts. The child's own descriptor lives at that path and is loaded via `load_package` during recursive resolution.
2. Phase 1 exposes `stale_report(root_pkg, changed_paths) -> list[StaleNode]` and `mark_stale(graph, changed_paths, package_root) -> StaleSet` (has `reasons: dict[node_id -> str]`). There is no `build_stale_graph` and no reason enum — reasons are free-form strings like `"owned path matched: X"` or `"upstream stale: Y"`.

**Files:**
- Create `src/opencode_arch/mcp/tools/lifecycle/package_children_add.py`
- Create `src/opencode_arch/mcp/tools/lifecycle/package_stale.py`
- Update server.py.
- Create `tests/mcp/tools/lifecycle/test_package_children_add.py`, `test_package_stale.py`.

**Spec:**
- `architect_package_children_add(repo_path, child_path) -> {ok, parent_architecture_id, children: [str]}`.
  - `child_path` is a POSIX-relative path string (relative to the root package's directory) pointing to an existing `package.yaml`.
  - Reads root `package.yaml` (raw YAML text), appends `child_path` to the `children:` list, writes atomically via `architecture_model.lifecycle.atomic_store.write_atomic`, then re-loads via `load_package` to validate the resulting descriptor tree.
  - Returns updated children list and the root `architecture_id`.
  - Idempotence: If `child_path` already present → `err("PRECONDITION_FAILED", "child already present", child_path=...)`.
  - If child file does not exist → `err("NOT_FOUND", "child package.yaml not found", child_path=...)`.
  - If root `package.yaml` missing → `err("NOT_FOUND", "package.yaml not found")`.
  - If re-load after write raises `ValidationError` → `err("SCHEMA_VIOLATION", "resulting descriptor invalid", detail=str(e))` (write should ideally roll back; document if it doesn't).
- `architect_package_stale(repo_path, changed_paths: list[str]) -> {ok, stale: [{node_id, kind, owned_paths, inputs, digest, reason}]}`.
  - `changed_paths` are POSIX-relative to the root package. Required (may be empty list → empty stale list).
  - Internally: `graph = build_graph(root_pkg); ss = mark_stale(graph, [Path(root_pkg.root)/p for p in changed_paths], package_root=root_pkg.root)`.
  - Then join `ss.nodes` × `ss.reasons` × `graph.nodes()` to emit records with `reason` field (free-form string from Phase 1).
  - Sort deterministically by `(kind, node_id)`.
  - No cache file usage from this tool (avoid mutating `.architecture/stale.yaml`; that's `stale_report`'s side effect). If we want caching, we can call `stale_report` in a later hardening pass.
  - If root `package.yaml` missing → `err("NOT_FOUND", "package.yaml not found")`.

**Commit:** `feat(mcp): add package children-add and stale tools`

**Follow-up (non-blocking):** Rename T4's `parent_package_id` parameter to `expected_root_id` in a small hygiene commit before Group C begins, per T4 reviewer's directive. Not tracked as a separate task; batch into T22 (CLI) or a standalone `chore(mcp)` commit.

---

### Group C — slice/view/artifact endpoints (T8-T12)

#### T8: `architect_slice_materialize`

**AMENDED.** Phase 1's `ModelSlice` is a full Pydantic contract requiring `id`, `contract_version`, `architecture_id`, `model_revision`, `scope`, `closure`, `shared_refs`, `selectors` (min one dimension), plus optional `curation`/`parameters`/`generated_at`/`signatures`. `curation` alone is insufficient input. The tool takes the full slice spec dict.

**Files:**
- Create `src/opencode_arch/mcp/tools/lifecycle/slice_materialize.py`
- Update server.py.
- Create `tests/mcp/tools/lifecycle/test_slice_materialize.py`

**Spec:**
- `architect_slice_materialize(repo_path, slice_spec: dict, persist: bool = True) -> dict`.
- Behavior:
  1. `resolve_repo(repo_path)`.
  2. Load root package from `<repo>/.architecture/lifecycle/package.yaml`.
  3. Parse `slice_spec` via `ModelSlice(**slice_spec)`. `ValidationError` → `err("SCHEMA_VIOLATION", "invalid slice spec", detail=str(e))`. `ModelSlice.contract_version` is auto-defaulted; if caller supplies a mismatched version Phase 1 raises → surfaces as SCHEMA_VIOLATION.
  4. If `slice.scope == "federated"` → `err("PRECONDITION_FAILED", "federated scope not supported without registry resolver")` for now (T21 wires the federated resolver).
  5. Call `materialize(slice, pkg)`. Any `FileNotFoundError` from missing model → `err("NOT_FOUND", "package model not found")`.
  6. Compute `digest = compute_slice_digest(slice)`.
  7. If `persist=True`, write the input `slice_spec` (with `generated_at` timestamp injected if absent) to `<repo>/.architecture/lifecycle/slices/<slice_id>.yaml` via `write_atomic`.
  8. Return `ok({"slice_id": ms.slice_id, "architecture_id": ms.architecture_id, "model_revision": ms.model_revision, "digest": digest, "stub_entity_ids": list(ms.stub_entity_ids), "warnings": [{"code": w.code, "message": w.message, "entity_id": w.entity_id} for w in ms.warnings], "fragment": ms.model_fragment.model_dump(mode="json"), "persisted_path": <relative-str or None>})`.
- If root `package.yaml` missing → `err("NOT_FOUND", "package.yaml not found")`.

**Commit:** `feat(mcp): add slice materialize tool`

---

#### T9: `architect_view_project` + `architect_view_render`

**AMENDED.** Phase 1's `project(view, materialized_slice)` needs a `MaterializedSlice`, not a raw `slice_id`. Renderers need an `ArtifactSpec`, not a bare `format` string. T9 loads a persisted slice from T8's `slices/<id>.yaml` directory, re-materializes it, then projects/renders.

**Files:**
- Create `src/opencode_arch/mcp/tools/lifecycle/view_project.py`
- Create `src/opencode_arch/mcp/tools/lifecycle/view_render.py`
- Create `src/opencode_arch/mcp/tools/lifecycle/_view_common.py` — shared slice-load + materialize + parse helpers.
- Update server.py.
- Create `tests/mcp/tools/lifecycle/test_view_project.py`, `test_view_render.py`.

**Spec:**
- `architect_view_project(repo_path, view_spec: dict, slice_id: str) -> dict`.
  - Load persisted slice from `<lifecycle>/slices/<slice_id>.yaml`; missing → `err("NOT_FOUND", "slice not found", slice_id=...)`.
  - Parse `slice_spec` via `ModelSlice(**loaded)`; materialize via `materialize(slice, resolve_current_pkg(pkg))`.
  - Parse `ViewSpec(**view_spec)` → `SCHEMA_VIOLATION` on `ValidationError`.
  - Call `project(view, ms)`. On `ProjectorNotFound` → `err("NOT_FOUND", "projector not registered", projector=view.projector)`. On `SliceMismatch` → `err("PRECONDITION_FAILED", "slice_ref does not match materialized slice")`.
  - Return `ok({"view_id": pv.view_id, "slice_id": pv.slice_id, "model_revision": pv.model_revision, "diagram_spec": <serialized DiagramSpec>, "provenance": pv.provenance, "warnings": list(pv.warnings)})`.
- `architect_view_render(repo_path, view_spec: dict, slice_id: str, artifact_spec: dict) -> dict`.
  - Same slice-load + materialize + project chain.
  - Parse `ArtifactSpec(**artifact_spec)` → `SCHEMA_VIOLATION` on `ValidationError`.
  - If `artifact.renderer == "zip"` → `err("PRECONDITION_FAILED", "zip renderer requires bundle resolver, not yet supported")`.
  - Look up renderer via `get_renderer(artifact.renderer)`; call `renderer(pv, artifact) -> bytes`.
  - Content-type map: `svg`→`image/svg+xml`, `markdown`→`text/markdown`, `html`→`text/html`, `ai-context`→`text/plain`.
  - All current Phase 1 renderers return text; return `body_utf8: str`, `body_base64: None`.
  - Return `ok({"artifact_id": artifact.id, "content_type": <str>, "body_utf8": <str>, "body_base64": None, "digest": <sha256 hex of bytes>, "warnings": list(pv.warnings)})`.

**Commit:** `feat(mcp): add view projection and render tools`

---

#### T10: `architect_artifact_plan`

**Files:**
- Create `src/opencode_arch/mcp/tools/lifecycle/artifact_plan.py`
- Update server.py.
- Create `tests/mcp/tools/lifecycle/test_artifact_plan.py`

**Spec:**
- `architect_artifact_plan(repo_path, artifact_specs:[dict]) -> {ok, plan:{nodes:[{spec_id, depends_on:[]}], order:[]}}`.
- Uses `ArtifactDAG` from bridge; detects cycles → `PRECONDITION_FAILED` with cycle nodes.

**Commit:** `feat(mcp): add artifact rebuild plan tool`

---

#### T11: Rebuild executor (`lifecycle_exec.rebuild`)

**Files:**
- Create `src/opencode_arch/lifecycle_exec/rebuild.py`
- Create `tests/lifecycle_exec/test_rebuild.py`

**Spec:**
- `rebuild_artifacts(repo_path, artifact_specs, *, force=False) -> RebuildReport{built:[], skipped:[], failed:[], journal_events:[]}`.
- For each node in `ArtifactDAG.topological_order()`:
  - If output already exists and its digest matches `ArtifactSpec.expected_digest` and `force=False`: skip.
  - Else: materialize input slice → project via view → render via artifact format → atomic-write to `<repo>/.architecture/lifecycle/artifacts/<spec_id>.<ext>` → verify emitted digest.
- Journal event per outcome: `artifact.built`, `artifact.skipped`, `artifact.failed`.
- No MCP registration in this task (T12 registers).

**Commit:** `feat(lifecycle_exec): add artifact rebuild runner`

---

#### T12: `architect_artifact_rebuild` MCP tool

**Files:**
- Create `src/opencode_arch/mcp/tools/lifecycle/artifact_rebuild.py`
- Update server.py.
- Create `tests/mcp/tools/lifecycle/test_artifact_rebuild.py`

**Spec:**
- `architect_artifact_rebuild(repo_path, artifact_specs:[dict], force:bool=False) -> {ok, built:[], skipped:[], failed:[]}`.
- Wraps `lifecycle_exec.rebuild.rebuild_artifacts`.
- `failed` non-empty → still `ok: True` but reports failures per artifact.

**Commit:** `feat(mcp): add artifact rebuild MCP tool`

---

### Group D — AI work-order endpoints (T13-T17)

#### T13: `architect_workorder_submit`

**Files:**
- Create `src/opencode_arch/mcp/tools/ai/workorder_submit.py`
- Update server.py.
- Create `tests/mcp/tools/ai/test_workorder_submit.py`

**Spec:**
- `architect_workorder_submit(repo_path, work_order:dict) -> {ok, work_order_id, job_id}`.
- Validates `work_order` against `spec/ai-work-order.schema.json`.
- Persists WorkOrder YAML at `<repo>/.architecture/ai/workorders/<id>.yaml` (atomic).
- Creates a `Job` in `draft` state referencing the WorkOrder.
- Journal event: `ai.workorder.submit`.

**Commit:** `feat(mcp): add work-order submit tool`

---

#### T14: `architect_job_transition` + `architect_job_get`

**Files:**
- Create `src/opencode_arch/mcp/tools/ai/job_transition.py`
- Create `src/opencode_arch/mcp/tools/ai/job_get.py`
- Update server.py.
- Create `tests/mcp/tools/ai/test_job_transition.py`, `test_job_get.py`.

**Spec:**
- `architect_job_get(repo_path, job_id) -> {ok, job:{...}}` — reads via `JobStore.get`.
- `architect_job_transition(repo_path, job_id, new_state, reason=None, actor=None, result_ref=None, error=None) -> {ok, job:{...}}`.
- On `InvalidTransitionError`: `err(PRECONDITION_FAILED, ...)` including `from_state`, `to_state`, `allowed`.

**Commit:** `feat(mcp): add job get and transition tools`

---

#### T15: Job worker (`lifecycle_exec.worker`)

**Files:**
- Create `src/opencode_arch/lifecycle_exec/worker.py`
- Create `tests/lifecycle_exec/test_worker.py`

**Spec:**
- `dequeue_next(repo_path) -> Job | None` — reads `JobStore.list_ids()`, returns oldest job in `queued` state (by `created_at`).
- `run_job(repo_path, job_id, *, proposer:Callable[[WorkOrder], Proposal]) -> Job` — transitions queued→running, calls `proposer(work_order)` to get a Proposal, transitions running→validating, invokes `validate_proposal`, transitions to `completed` (with `result_ref` = path to persisted proposal) if valid else `failed` (with error message).
- Proposer callable is injected — Phase 2 does NOT hardwire an LLM; a stub for tests and a hook for future integration.
- Persists proposal at `<repo>/.architecture/ai/proposals/<job_id>.yaml`.

**Commit:** `feat(lifecycle_exec): add work-order job worker`

---

#### T16: `architect_job_run` MCP tool (stub proposer)

**Files:**
- Create `src/opencode_arch/mcp/tools/ai/job_run.py`
- Update server.py.
- Create `tests/mcp/tools/ai/test_job_run.py`

**Spec:**
- `architect_job_run(repo_path, job_id) -> {ok, job:{...}, proposal_ref}`.
- Uses a `StubProposer` that reads a proposer plugin path from `.architecture/ai/proposer_config.yaml` (optional). If absent, returns `err(PRECONDITION_FAILED, "no proposer configured")`.
- Real LLM integration deferred to Phase 3; this task wires the plumbing and validates the wiring via a test-fixture proposer.

**Commit:** `feat(mcp): add job run tool with pluggable proposer`

---

#### T17: `architect_proposal_validate`

**Files:**
- Create `src/opencode_arch/mcp/tools/ai/proposal_validate.py`
- Update server.py.
- Create `tests/mcp/tools/ai/test_proposal_validate.py`

**Spec:**
- `architect_proposal_validate(repo_path, proposal:dict, work_order_id, slice_ids:[str]) -> {ok, report:{passed, findings:[]}}`.
- Loads WorkOrder + slices from disk, runs `validate_proposal`.

**Commit:** `feat(mcp): add proposal validate tool`

---

### Group E — proposal apply + merge (T18-T20)

#### T18: Proposal apply executor

**Files:**
- Create `src/opencode_arch/lifecycle_exec/apply.py`
- Create `tests/lifecycle_exec/test_apply.py`

**Spec:**
- `apply_proposal(repo_path, proposal, *, dry_run=True) -> ApplyReport{changes:[], new_revision, digest, journal_events:[]}`.
- Per-kind appliers:
  - `ModelPatch`: apply ops to loaded model → new revision.
  - `DecompositionProposal`: create child packages under parent, atomic.
  - `SliceProposal`: persist slice to `.architecture/lifecycle/slices/`.
  - `ViewCurationProposal`: persist view_spec to `.architecture/lifecycle/views/`.
  - `ArtifactCandidate`: persist artifact_spec to `.architecture/lifecycle/artifacts_specs/`.
  - `ImpactAssessment`: read-only; returns report but writes no model changes.
- `dry_run=True`: computes what would change without writing.
- Cross-revision drift check runs BEFORE apply — same rule as validator.

**Commit:** `feat(lifecycle_exec): add proposal apply runner`

---

#### T19: `architect_proposal_apply` MCP tool

**Files:**
- Create `src/opencode_arch/mcp/tools/ai/proposal_apply.py`
- Update server.py.
- Create `tests/mcp/tools/ai/test_proposal_apply.py`

**Spec:**
- `architect_proposal_apply(repo_path, proposal:dict, work_order_id, dry_run:bool=True) -> {ok, report:{...}}`.
- Requires job in `completed` state referencing the proposal (else `PRECONDITION_FAILED`).
- Journal event: `ai.proposal.apply`.

**Commit:** `feat(mcp): add proposal apply MCP tool`

---

#### T20: Three-way merge

**Files:**
- Create `src/opencode_arch/lifecycle_exec/merge.py`
- Create `src/opencode_arch/mcp/tools/lifecycle/package_merge.py`
- Update server.py.
- Create `tests/lifecycle_exec/test_merge.py`, `tests/mcp/tools/lifecycle/test_package_merge.py`.

**Spec:**
- `three_way_merge(base, local, remote) -> MergeResult{merged_model, conflicts:[{entity_id, field, base, local, remote}]}`.
- Auto-merge when only one side changed a field; conflict when both sides changed differently.
- Entity-level diff: additions on either side merge in; removals conflict if the other side modified.
- Relationship-level: unique on `(from, to, type)` tuple.
- MCP: `architect_package_merge(repo_path, base_revision, local_revision, remote_revision) -> {ok, merged_digest, conflicts:[]}`.

**Commit:** `feat(lifecycle_exec): add three-way merge with MCP wrapper`

---

### Group F — federation + CLI + integration (T21-T24)

#### T21: Federated registry resolver

**Files:**
- Create `src/opencode_arch/lifecycle_exec/federation.py`
- Create `tests/lifecycle_exec/test_federation.py`

**Spec:**
- `FederatedRegistry` — holds a list of local registry roots (paths).
- `resolve(package_id, revision=None) -> (root, descriptor)` — searches each root for matching package.
- `add_root(path)`, `list_roots()`, `remove_root(path)`.
- No cryptographic signing (deferred to Phase 3).
- Persistent config at `~/.opencode-arch/federation.yaml`.

**Commit:** `feat(lifecycle_exec): add federated registry resolver`

---

#### T22: CLI wiring for lifecycle commands

**Files:**
- Create `src/opencode_arch/cli/lifecycle.py`
- Update `src/opencode_arch/cli/main.py` (add subcommand group; do not reorder existing).
- Create `tests/cli/test_lifecycle_cli.py`.

**Spec:**
- `opencode-arch lifecycle publish --model <yaml> [--manifest <json>] [--parent <id>]`
- `opencode-arch lifecycle load <package_id> [--revision <rev>]`
- `opencode-arch lifecycle stale`
- `opencode-arch lifecycle slice --id <slice_id> --curation <json>`
- `opencode-arch lifecycle rebuild [--force] --specs <path>`
- `opencode-arch lifecycle merge --base <rev> --local <rev> --remote <rev>`
- `opencode-arch ai submit --work-order <yaml>`
- `opencode-arch ai job get <job_id>`
- `opencode-arch ai job transition <job_id> <new_state> [--result-ref <ref>] [--error <msg>]`
- `opencode-arch ai proposal validate --proposal <yaml> --workorder-id <id> --slice-ids <ids>`
- `opencode-arch ai proposal apply --proposal <yaml> --workorder-id <id> [--dry-run]`
- All commands print structured JSON on `--json`; human table otherwise.

**Commit:** `feat(cli): add lifecycle and AI subcommands`

---

#### T23: End-to-end integration test — full lifecycle round trip

**Files:**
- Create `tests/e2e/test_lifecycle_roundtrip.py` (opt-in; not in default suite).
- Create `tests/integration/test_mcp_lifecycle.py` (in default suite).

**Spec (integration):**
- Set up a temp repo with a small model.
- Call `architect_package_publish` → `architect_package_load` → verify digest match.
- Call `architect_slice_materialize` → `architect_view_project` → `architect_view_render(format="svg")` → assert body non-empty.
- Call `architect_artifact_plan` → `architect_artifact_rebuild` → verify artifact file exists on disk.
- Submit a WorkOrder → transition job → run with fixture proposer → validate → apply (dry-run).
- Assert journal has expected events in order.

**Spec (e2e, opt-in):**
- Same flow but using CLI subprocess calls.

**Commit:** `test(integration): add MCP lifecycle round-trip and e2e scaffold`

---

#### T24: Phase 2 completion report + CONTEXT.md update

**Files:**
- Append `## Phase 2 completion report` section to plan.
- Update `CONTEXT.md` with new tool inventory and lifecycle_exec package.

**Commit:** `docs(plan): mark Phase 2 complete and update CONTEXT`

---

## Phase 2 exit criteria

1. Full suite: 452 + N passed (N = sum of new tests across T1-T23), 2 pre-existing failures unchanged, no new failures.
2. All 22 new MCP tools registered and callable via `mcp` protocol (verified by an inspect test in T23).
3. `lifecycle_exec` package has no MCP dependencies (unit-testable standalone).
4. No modifications to existing tool modules under `src/opencode_arch/mcp/tools/*.py` (top-level) — new tools live in `lifecycle/` and `ai/` subdirectories.
5. Journal events appear for every state change (publish, transition, apply, rebuild).
6. `phase 1` HEAD `7f0c7dc` imports cleanly at test time via PYTHONPATH.
7. CLI passes `--help` for every new subcommand.

## Out of scope for Phase 2

- Cryptographic signing / signed federation.
- Real LLM proposer integration (only fixture proposer in T16).
- Web UI / dashboard.
- Multi-repo cross-federation policies beyond `add_root`.
- Backwards-compat migration of pre-Phase-1 `.architecture-model.yaml` layout.

## Notes for implementer subagents

- Every task: TDD strictly. Write failing tests first, then implement.
- Never `pip install -e` anything.
- Never stage `.architecture/*`, `.architecture-models/*`, `.architecture-model.yaml`.
- Use combined implementer + reviewer subagent pattern from Phase 1.
- Every task ends with the full-suite baseline command passing.
