# API Detail — CAP-REGEN: Subsystem Regen-Loop

## Overview

| Field | Value |
|-------|-------|
| ID | CAP-REGEN |
| F-Block | F1 (Core Workflows) |
| Priority | High |
| Realized by | COMP-CLI (`cli/regen_loop.py`) |
| Actor | Developer via CLI |
| Constraints | CON-TIMEOUT |

---

## Primary API

### `run_regen_loop(...)` (orchestrator in `cli/regen_loop.py`)

The subsystem-decomposed code regeneration pipeline. Decomposes a project into subsystems, iterates per-subsystem until tests pass, supports blind mode (model-only, no source access).

**High-Level Algorithm:**

1. Load architecture model from `.architecture-model.yaml`
2. Call `test_affinity_decompose(repo_path)` → list of Subsystems
3. For each subsystem (topologically sorted, leaves first):
   a. Get adaptations from learning module (`get_adaptations()`)
   b. Build prompt with model context (constants, signatures, test contracts, dep context)
   c. Compute `PromptMetrics` (compression ratio, token breakdown)
   d. In blind mode: run in temp dir with no source access
   e. In normal mode: run in actual repo
   f. Call `runner.run(prompt, work_dir)`
   g. Run subsystem tests via `run_subsystem_tests(test_files, repo_path)`
   h. If failing: `classify_failures()` → build feedback → iterate (up to max_iterations)
   i. If passing: mark converged
4. Run full test suite
5. Generate report card via assessor
6. Record telemetry (learning curve, regen outcomes)

---

## Supporting Functions

### `run_subsystem_tests(test_files: list[Path], repo_path: Path) -> dict`

Runs pytest on specific test files for a subsystem.

**Returns:**

| Key | Type | Description |
|-----|------|-------------|
| `passed` | `int` | Tests that passed |
| `failed` | `int` | Tests that failed |
| `total` | `int` | Total tests collected |
| `pass_rate` | `float` | passed/total (0.0-1.0) |
| `output` | `str` | Raw pytest stdout+stderr |

Implementation: Invokes `python -m pytest <files> -v --tb=short -q` with 120s timeout.

---

### `PromptMetrics` (dataclass)

Token accounting for each regen prompt:

| Field | Type | Description |
|-------|------|-------------|
| `total_tokens` | `int` | Total prompt size |
| `model_context_tokens` | `int` | Architecture model context |
| `signatures_tokens` | `int` | Function signatures section |
| `constants_tokens` | `int` | Constants section |
| `contracts_tokens` | `int` | Test contracts section |
| `dependency_tokens` | `int` | Upstream dependency context |
| `feedback_tokens` | `int` | Failure feedback (iteration > 1) |
| `source_equivalent_tokens` | `int` | What agent would read without model |
| `compression_ratio` | `float` | source_equivalent / total |

---

## Behavioral View: BEH-REGEN

**Trigger:** `opencode-arch regen-loop --repo <path> [--blind] [--max-iterations N]`

**Pattern:** Pipeline (iterate per-subsystem)

```
Developer ──► CLI (regen-loop)
                │
                ├─► Load model
                ├─► test_affinity_decompose(repo) → [Subsystem]
                │
                │   ┌─── FOR EACH subsystem (topological order) ───┐
                │   │                                               │
                │   ├─► get_adaptations() from learning module      │
                │   ├─► Build prompt (model + sigs + constants +    │
                │   │   contracts + dep context)                    │
                │   ├─► Compute PromptMetrics                       │
                │   │                                               │
                │   │   ┌── ITERATE until pass or max_iterations ──┐│
                │   │   ├─► runner.run(prompt, work_dir)            ││
                │   │   ├─► run_subsystem_tests()                   ││
                │   │   ├─► IF failing:                             ││
                │   │   │   ├─► classify_failures()                 ││
                │   │   │   ├─► analyze_gaps()                      ││
                │   │   │   └─► build feedback prompt               ││
                │   │   └──────────────────────────────────────────-┘│
                │   │                                               │
                │   ├─► Record regen outcome (telemetry)            │
                │   └───────────────────────────────────────────────┘
                │
                ├─► Run full test suite
                ├─► Generate report card (assessor)
                ├─► Record learning curve
                │
Developer ◄── report (grade, fidelity, compression, actions)
```

**Blind mode:** Agent works in an empty temp directory with ONLY the model data (constants, signatures, body_hints, test_contracts) in its prompt. Proves the model is a sufficient behavioral representation.

**Normal mode:** Agent works in the actual repo with full file access. Model context still provided for guidance.
