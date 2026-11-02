---
name: extraction
description: "Use when extracting architecture from a codebase, running the pipeline, decomposing systems, or any request to produce an architecture model from source code"
---

# Architecture Extraction

## Overview

The live tools are **openAG** (graph-native). The model works in two phases:
**write the model once, then read it.** One writer tool scans the source and
persists a v3 model; every other `arch_*` tool reads that model.

**Core principle:** A writer (`arch_pipeline` or `arch_extract`) must run
**first** to populate `<repo>/.architecture/model/model.v3.yaml`. Until it
does, every reader raises `FileNotFoundError: openAG model dir not found/empty`.

**Expect a coarse model.** Extraction is Python-AST-only. The seed is one
System + one Component claiming every scanned file, refined by a deterministic
B-ROUND fixpoint. There is **no LLM enrichment, no uncertainty-resolution
loop, no per-stage quality score.** Do not try to make it richer through tool
params — they are inert (see Common Mistakes).

## When This Skill Applies

- "Extract the repo / architecture"
- "Decompose this system"
- "Run the pipeline"
- "Analyze / model the architecture"
- Any request to produce an architecture model from source code

## Canonical Workflow

Run these as single tool calls, in order. Step 0 is mandatory and first; the
rest are reads you can run as needed.

### Step 0 — Write the model (REQUIRED, run first)

```
arch_pipeline(repo_path="/abs/path/to/repo")
```

Scans `<repo>/src` (or the repo root if there is no `src/`), runs the B-ROUND
fixpoint, and writes both `.architecture/model/model.v3.yaml` and a generation
under `.architecture/generations/openAG-tool`. Returns:

```
{generation, model_dir, stage, iterations, converged,
 grounded, ungrounded, gaps, entities}
```

Use `arch_extract(repo_path=...)` instead for a lighter scan→extract+commit
without the fixpoint/grounding summary. Either one populates the model dir.

### Step 1 — Validate / gate the written model

- `arch_validate(repo_path=...)` → schema + axis-lint score (0–100).
- `arch_check(repo_path=...)` → representativeness vs the code ground graph.
- `arch_gate(repo_path=...)` → L2 go/no-go over owed + completeness gaps.

### Step 2 — Inspect structure (read-only, any order)

- `arch_evaluate(repo_path=...)` → one-shot health rollup (score, band,
  coverage, requirement count). This is where the overall score comes from —
  **not** from the writer's stage output.
- `arch_health(repo_path=...)` → graph-wide or per-node health.
- `arch_frontier(repo_path=...)` → ready-promise node ids. **Preferred
  discovery entry point:** take a node id from here and drill in with
  `arch_owed`, `arch_gaps`, `arch_slice`, or `arch_round(node_id=...)`. On a
  coarse/fully-gapped model the frontier is often **empty** (no promise is
  "ready") — in that case get node ids from `arch_health` (`worst_offenders`)
  or `arch_decompose` instead, then drill in the same way.
- `arch_scan(repo_path=...)` → raw module / import-edge inventory of the source
  tree (does not require the model dir).
- `arch_decompose(repo_path=...)` / `arch_group(repo_path=...)` → System
  decomposition and module grouping.
- `arch_compliance(repo_path=...)`, `arch_docs(repo_path=...)`.

### Step 3 — Change tracking

- `arch_diff(repo_path=...)` → diff the working model against git HEAD's model
  (only meaningful after a writer has produced a working-tree model).

## Tool Reference

| Tool | Role | Reads / Writes |
|------|------|----------------|
| `arch_pipeline` | writer | writes model dir + generation (B-ROUND fixpoint) |
| `arch_extract` | writer | writes model dir + generation (scan→extract) |
| `arch_scan` | reader | module / import-edge inventory (no model dir needed) |
| `arch_evaluate` | reader | health score / band / coverage |
| `arch_validate` | reader | schema + axis-lint score |
| `arch_check` | reader | representativeness vs ground graph |
| `arch_gate` | reader | L2 go/no-go gaps |
| `arch_health` | reader | graph-wide / per-node health |
| `arch_frontier` | reader | ready-promise node ids (discovery entry) |
| `arch_owed` | reader | owed promises for a `node_id` |
| `arch_gaps` | reader | typed gaps for a `node_id` |
| `arch_slice` | reader | entity-scoped sub-doc for a `node_id` |
| `arch_round` | reader | deterministic grounded digest |
| `arch_decompose` | reader | System decomposition + split candidates |
| `arch_group` | reader | module grouping (A1 partition) |
| `arch_compliance` | reader | matrix / axes / scoring report |
| `arch_docs` | reader | generated SE docs |
| `arch_diff` | reader | diff working model vs git HEAD |

For exact params of any tool, read its MCP docstring. Node-scoped readers
(`arch_owed`, `arch_gaps`, `arch_slice`, `arch_round`) take a `node_id` — get
it from `arch_frontier` (or `arch_health`/`arch_decompose`) first.

## This Is NOT the Legacy AMS Flow

<!-- legacy-ok:start -->
If you remember an `architect_pipeline` 10-stage loop, discard it. The live
tools do **not** have any of the following:

- No `architect_pipeline` / `architect_scan` / `architect_slice` — the tools
  are `arch_pipeline`, `arch_scan`, `arch_slice`.
- No 10 discrete content-producing stages (observe→emit).
- No `uncertainties_to_resolve` field, no resolution loop, no HARD-GATE.
- No per-stage 0–100 quality score (scores come from `arch_evaluate` /
  `arch_validate`, not the writer).
- No decompose pause / interactive confirmation.
- No scoped per-subsystem enrichment sub-pipelines.
- No `.architecture-models/` artifact tree. Output is
  `.architecture/model/model.v3.yaml` + `.architecture/generations/`.
<!-- legacy-ok:end -->

## Common Mistakes

| Mistake | Reality |
|---------|---------|
| Reading (`arch_health`, `arch_frontier`, …) before a writer ran | Raises `FileNotFoundError: openAG model dir not found/empty`. Run `arch_pipeline` first. |
| Passing `stage=`, `resolutions=`, `clear_cache=`, `scope=` to `arch_pipeline` expecting staged/enriched behavior | These params are accepted for compatibility but **ignored** (`stage` is only echoed back). The result is identical. |
| Passing `model_yaml=` / `context_tokens=` to `arch_extract` | Ignored — the model is derived from source, not a YAML blob. |
| Looping stages to raise the score | Each call just increments the generation counter; entities/gaps do not change. One writer call is enough. |
| Expecting a systems list from the writer's `decompose` output | Use `arch_decompose` for decomposition; the writer does not return systems. |
| Expecting rich, enriched entities | The model is Python-AST-only and coarse by design. |
| Alarmed that `arch_gate` reports `blocked`/band F while `arch_validate` scores 100 | Expected on a coarse model: `validate` checks schema/axes; `gate` measures owed + completeness gaps, which are unfilled until the model is enriched. Not a failure. |
| `arch_frontier` returns `[]` so there is "no entry point" | Normal for a fully-gapped model. Get node ids from `arch_health` (`worst_offenders`) or `arch_decompose`, then use the node-scoped readers. |
| `arch_diff` shows all entities as "removed" | Artifact of a fresh repo with no committed model in git HEAD (empty baseline), not a diff error. |
