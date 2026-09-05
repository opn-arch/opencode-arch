# opencode-arch AMS API Adoption Plan

**Date:** 2026-09-05
**Branch:** `feat/ams-api-adoption` (based on `main` @ `531b845`)
**Worktree:** `.worktrees/ams-api-adoption`
**Depends on:** architecture-model-standard `feat/curated-se-views` @ `27458c0` (Phase 1 escalations merged) via `PYTHONPATH="$PWD/src:/Users/baigm2/Documents/Projects/architecture-model-standard/.worktrees/curated-se-views/src"`

**Goal:** Adopt new public APIs from architecture-model-standard Phase 1 escalations, removing private-symbol reliance and reducing duplicated inline logic. **Scope B** per user selection.

**Baseline:** 917 passed, 2 pre-existing failures (`test_adaptive_budget.py::test_very_large_repo_capped`, `test_ingest.py::test_ingest_basic`). Never regress; do not fix these.

**Constraints:**
- Never `git add -A` — explicit paths only.
- Never touch `.architecture*` telemetry.
- Never `pip install -e` (breaks fastmcp per CONTEXT).
- All API adoptions must preserve behavior — mechanical refactor, tests are the safety net.
- Conventional Commit style, one commit per task.

**Test command (all tasks):**
```
PYTHONPATH="$PWD/src:/Users/baigm2/Documents/Projects/architecture-model-standard/.worktrees/curated-se-views/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/e2e
```

---

## Task 1: Adopt `generation_dir` (rename `_generation_dir` imports)

**Files:**
- `src/opencode_arch/mcp/tools/lifecycle/package_load.py` (line 51 import, line 85 call)
- `src/opencode_arch/mcp/tools/lifecycle/package_merge.py` (line 82 import, lines 134, 180)
- `src/opencode_arch/mcp/tools/lifecycle/package_diff.py` (line 57 import, lines 86, 89)
- `src/opencode_arch/cli/lifecycle.py` (lines 236, 272, 455, 492, 535)

**Change:** replace `from architecture_model.lifecycle.publication import _generation_dir` (or wherever it's imported) with `from architecture_model.lifecycle import generation_dir` and update call sites. The old private symbol is still aliased upstream so this is behavior-preserving.

**Verify:** full test suite passes at baseline (917 passed, 2 pre-existing).

**Commit:** `refactor(lifecycle): adopt public generation_dir from ams`

---

## Task 2: Delegate `_apply_model_patch` to public `apply_model_patch`

**File:** `src/opencode_arch/lifecycle_exec/apply.py:323`

**Approach:** Inspect the private `_apply_model_patch` signature. If it wraps a proposal-application flow that matches the public `apply_model_patch(model, proposal)` semantics (add/remove/replace), refactor to delegate. If it does more (dry-run, report generation, filesystem writes), keep the wrapper but call the public helper for the core patch operation.

**Verify:** all `lifecycle_exec/test_apply.py` tests pass. Full suite at baseline.

**Commit:** `refactor(lifecycle_exec): delegate to ams apply_model_patch (N52 adoption)`

---

## Task 3: Adopt `current_root_digest(pkg)` for CURRENT-digest reads

**File:** `src/opencode_arch/lifecycle_exec/apply.py:200-213`

**Change:** replace the inline `_get_current_digest` (reads `pkg.root / "CURRENT" / "digest.json"`, parses JSON, extracts `root_digest`) with a call to `current_root_digest(pkg)`. Preserve the return-tuple contract by pairing with revision lookup.

**Leave alone:** other digest.json readers that access arbitrary generation dirs (`federation.py::_read_root_digest`, `package_load.py` inline), since `current_root_digest` only serves CURRENT.

**Verify:** `tests/lifecycle_exec/test_apply.py` passes. Full suite at baseline.

**Commit:** `refactor(lifecycle_exec): adopt current_root_digest helper (N53 adoption)`

---

## Task 4: Adopt `MaterializedSlice.to_dict()` in view helpers

**File:** `src/opencode_arch/mcp/tools/lifecycle/_view_common.py`

**Change:** find any location that serializes a `MaterializedSlice` (either by manual dict construction or `dataclasses.asdict`) and replace with `mslice.to_dict()`. Downstream consumers already expect the `fragment` key shape.

**Verify:** MCP view tests pass. Full suite at baseline.

**Commit:** `refactor(mcp/lifecycle): adopt MaterializedSlice.to_dict (N105 adoption)`

---

## Task 5: Adopt `WorkOrder.build()` factory + rely on `Provenance.proposal_id` auto-derive

**Files:**
- `tests/mcp/tools/ai/_proposer_fixtures.py:19,48`
- `tests/lifecycle_exec/test_worker.py:69,279,325`
- `tests/lifecycle_exec/test_apply.py:83`
- Any producer site constructing `WorkOrder(...)` directly (grep to confirm)

**Change:**
- For each direct `WorkOrder(...)` constructor, replace with `WorkOrder.build(...)` where fields align.
- For `Provenance(...)` calls that hard-code a `proposal_id`, drop the field and let it auto-derive; where downstream asserts on a specific ID, keep the explicit value.

**Verify:** all affected test files still pass. Full suite at baseline.

**Commit:** `refactor(ai): adopt WorkOrder.build and Provenance.proposal_id auto-derive (N100/N64)`

---

## Task 6: Verification report + CONTEXT update

- Append `## Completion report` to this plan.
- Update `CONTEXT.md` at repo root — note adoption of new AMS APIs.
- Confirm final suite: 917 passed + 2 pre-existing (or higher if we added confirmations).

**Commit:** `docs(ams-api-adoption): completion report`
