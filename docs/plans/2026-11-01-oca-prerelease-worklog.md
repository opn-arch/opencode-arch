# OCA Prerelease Worklog — Compatibility + Self-Improvement Loop

**Date:** 2026-11-01
**Branch:** `b-round-local-recursive`
**Commit range:** `45f26d6..6247b45` (16 commits)
**Companion plan:** `openAG/docs/plans/2026-11-01-prerelease-readiness-plan.md`
**Companion design:** `openAG/docs/plans/2026-11-01-prerelease-readiness-design.md`

## Purpose

Pre-release readiness for the graph-native **openAG** engine and its MCP
extension **opencode-arch** (OCA). Three release requirements drove this work:

1. **Perfect compatibility** — expose three high-value openAG entry points
   through OCA so agents can drive openAG without bespoke glue.
2. **Verified self-improvement** — close the learning loop end-to-end: mine a
   lesson, author a gated proposal, approve it, publish a new model generation.
3. **OpenCode process integrity** — superpowers skill hygiene (covered in the
   openAG design doc; no OCA code impact).

This worklog is the durable record of the OCA-side work. For the
agent/user-facing usage guide see `docs/arch-learning-tools.md`.

## Workstream 1 — Compatibility tools

Three new MCP tools wrapping openAG kernel/compliance/mining entry points.
Each handler uses lazy `openag.*` imports, the standard envelope
(`ok` / `err` / raise→`INVALID_ARGUMENT`), and loads the openAG model from
`<repo_path>/.architecture/model/`.

| Tool | Commits | Source |
| --- | --- | --- |
| `arch_grow` | `45f26d6` | `src/opencode_arch/mcp/tools/arch_grow.py` |
| `arch_mine` | `660e323` | `src/opencode_arch/mcp/tools/arch_mine.py` |
| `arch_compliance` | `dfc0a8b`, `006978b` | `src/opencode_arch/mcp/tools/arch_compliance.py` |

- **`arch_grow`** — standalone scoped forward-GROW operator. `no_provider=True`
  yields a pure-symbolic, deterministic run; otherwise a real provider is built
  via `make_provider`. Returns `{root, gaps, residue, a4_grounded,
  identity_gaps}`.
- **`arch_mine`** — reservoir-mining pass over opencode sessions. `db`,
  `reservoir`, and `ledger` are required; idempotent via the ledger. Reads the
  opencode sessions SQLite and narrows by `repo` / `session`.
- **`arch_compliance`** — one of openAG's compliance reports: `matrix`
  (model-independent static standard), `axes` (per-axis exploration), or
  `scoring` (bounded 0–100 score from owed-promise gaps).

## Workstream 2 — Self-improvement loop

A gated, two-step learning loop plus two new lesson miners and end-to-end
coverage.

| Component | Commits | Source |
| --- | --- | --- |
| `arch_learn` | `404ded2`, `bd1ace7` | `arch_learn.py` |
| `arch_learn_approve` + `_devloop.py` | `2167d54`, `a423324` | `arch_learn_approve.py`, `_devloop.py` |
| `llm_calls` miner | `dbbf0b3`, `0a54219` | `arch_lessons.py` |
| `reservoir` miner | `fd8f3b1`, `dda7549` | `arch_lessons.py` |
| deterministic e2e | `a5264f0` | `tests/e2e/test_self_improvement_loop.py` |
| marker gate | `ac48010` | `tests/e2e/conftest.py`, `pyproject.toml` |
| opt-in real-OpenCode e2e | `d8d18dc` | `tests/e2e/test_self_improvement_loop_opencode.py` |
| proposer polish | `6247b45` | `src/opencode_arch/devloop/opencode_proposer.py` |

### The loop

1. **`arch_learn`** materializes a draft `WorkOrder` from the top mined lesson
   and creates a Job in state `draft`. **It stops there** — nothing is applied.
2. **`arch_learn_approve`** releases the draft Job: it resolves a proposer
   (injected, else from `.architecture/ai/proposer_config.yaml`), authors a
   `ModelPatch`, applies it, and publishes a new model generation. Returns the
   new `package_revision_to` and `model_diff_digest`.

The gate between steps is deliberate: authoring/applying never happens without
an explicit approval call.

### Proposer contract

- Config: `.architecture/ai/proposer_config.yaml` with
  `plugin: "module.path:function_name"`.
- Plugin signature: `Callable[[WorkOrder], dict]` returning a ModelPatch
  `{"ops": [...]}`.
- Shipped real-OpenCode proposer: `opencode_arch.devloop.opencode_proposer:propose`
  (uses `MCPProvider().structured`; import-safe).
- `_resolve_proposer_from_config` error reasons: `no_proposer_configured`,
  `proposer_config_malformed`, `proposer_plugin_not_loadable`,
  `proposer_plugin_not_callable`.

### Lesson miners

`arch_lessons` now runs **7 signal miners**, including the new `llm_calls.jsonl`
signal and the `reservoir` contradiction signal (threshold 2), and builds a
`grounded_index` from verified promises.

### End-to-end coverage

- `tests/e2e/test_self_improvement_loop.py` — deterministic, 2 tests, runs by
  default.
- `tests/e2e/test_self_improvement_loop_opencode.py` — opt-in, gated by
  `@pytest.mark.opencode_live` + `skipif(not OPENCODE_LIVE)`.
- conftest `pytest_collection_modifyitems` gates only `@pytest.mark.e2e`
  benchmarks behind `--e2e`, so the deterministic loop runs without flags.
  Markers `e2e` + `opencode_live` registered in `pyproject.toml`.

## Verification evidence

Fresh runs (not subagent-reported):

- **OCA full suite:** 434 passed, 9 skipped
  (`--ignore=tests/logs_db/test_client.py`, missing `respx`).
- **e2e:** 2 passed, 6 skipped (opt-in real-OpenCode tests skipped by default).
- **MCP `@mcp.tool()` count:** 61 (56 baseline + 5 new = 3 WS1 + 2 WS2).

## Known caveats

- **Tool-count drift (not a defect):** the plan quoted "59" tools; it
  undercounted the two learning-loop tools (`arch_learn`,
  `arch_learn_approve`). Actual total is 61.
- **openAG environmental failures:** openAG's full suite shows 16 pre-existing
  failures (`test_witness_*`, `test_graph_*`, `test_heller_witness`) asserting
  hard-coded counts against the external `heller-cell-model` repo, which drifted
  295→304 relationships. These are environmental, not regressions — none of the
  failing tests import `lessons`, and the lessons surface passes 45/45.

## Cross-repo notes

- **openAG** (branch `main`): engine-side changes to `src/openag/kernel/lessons.py`
  (7 miners) with tests; archive + verification-note commits `b68355e`,
  `29a6640`.
- **CONTEXT trims** in OCA / AMS working trees are intentionally **uncommitted**
  (CONTEXT.md is a never-commit file); full history archived at
  `openAG/docs/history/CONTEXT-archive.md`.
