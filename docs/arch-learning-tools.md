# Architecture Learning & Compatibility Tools

A task-oriented guide to the five OCA MCP tools that drive the graph-native
**openAG** engine: three compatibility tools and the two-step self-improvement
loop. This is a usage manual — for the build history and verification evidence
see `docs/plans/2026-11-01-oca-prerelease-worklog.md`.

## Overview

| Tool | What it does |
| --- | --- |
| `arch_grow` | Run the scoped forward-GROW operator over a model and report gaps/residue. |
| `arch_mine` | Mine opencode sessions into a reservoir of candidate lessons. |
| `arch_compliance` | Produce a compliance report (matrix / axes / scoring). |
| `arch_learn` | Materialize a **draft** proposal from the top mined lesson (gated). |
| `arch_learn_approve` | Approve a draft: author, apply, and publish a new model generation. |

All five load the openAG model from `<repo_path>/.architecture/model/`.

## Envelope & error convention

Every tool returns a JSON envelope:

```jsonc
// success
{ "ok": true,  "<payload fields>": ... }
// failure
{ "ok": false, "error": { "code": "...", "details": { "reason": "..." } } }
```

Check `env["ok"]` first. On failure read `env["error"]["code"]` and, when
present, `env["error"]["details"]["reason"]`. Common codes:

- `INVALID_ARGUMENT` — bad/missing argument (e.g. empty `root`, missing `db`).
- `NOT_FOUND` — repo or a required artifact is missing.
- `PRECONDITION_FAILED` — operation not allowed in the current state
  (e.g. approving a Job that is not `draft`).

## Tool reference

### `arch_grow`

Run the standalone scoped forward-GROW operator.

```
arch_grow(repo_path, *, root, budget=100.0, max_iterations=8,
          model=None, no_provider=False)
```

- **`root`** (required) — entity id to grow from.
- **`no_provider=True`** — pure-symbolic, deterministic run (no LLM provider).
- **Returns:** `{ root, gaps, residue, a4_grounded, identity_gaps }`.

```python
env = await arch_grow(repo_path, root="COMP-3", no_provider=True)
# env["gaps"], env["residue"], env["identity_gaps"]
```

### `arch_mine`

Reservoir-mining pass over opencode sessions. Idempotent via the ledger.

```
arch_mine(repo_path, *, db, reservoir, ledger,
          repo=None, session=None, model=None, provider=None)
```

- **`db`, `reservoir`, `ledger`** (all required) — opencode sessions SQLite,
  reservoir path, and dedup ledger path.
- **`repo` / `session`** — narrow mined chunks to a repo slug / session id.
- **Returns:** the `mine_run(...)` result.

```python
env = await arch_mine(
    repo_path,
    db="/path/to/opencode/sessions.sqlite",
    reservoir="/path/to/reservoir.jsonl",
    ledger="/path/to/ledger.jsonl",
)
```

### `arch_compliance`

Return one of openAG's compliance reports.

```
arch_compliance(repo_path, *, report="matrix")
```

- **`report`** — one of:
  - `matrix` (default) — model-independent static standard → `{ matrix }`
  - `axes` — per-axis exploration of the loaded model → `{ axes }`
  - `scoring` — bounded 0–100 score from owed-promise gaps → `{ score }`

```python
env = await arch_compliance(repo_path, report="scoring")
# env["score"]  -> 0..100
```

### `arch_learn`

Materialize a **draft** WorkOrder from the top mined lesson, and create a Job in
state `draft`. **Nothing is applied** — this is the gate.

```
arch_learn(repo_path, subject=None, lesson_type=None)
```

- **`subject` / `lesson_type`** — optional filters to steer lesson selection.
- **Returns:** `{ work_order_id, job_id, job_state: "draft", intent }`.

```python
env = await arch_learn(repo_path)
job_id = env["job_id"]          # feed into arch_learn_approve
```

### `arch_learn_approve`

Release a draft Job: author a `ModelPatch` via the proposer, apply it, and
publish a new model generation.

```
arch_learn_approve(repo_path, *, job_id, dry_run=False, proposer=None)
```

- **`job_id`** (required) — the draft Job from `arch_learn`.
- **`dry_run=True`** — author + validate without publishing.
- **`proposer`** — inject a proposer callable; otherwise resolved from
  `.architecture/ai/proposer_config.yaml`.
- **Returns on success:** `{ job_state: "completed", applied: true,
  package_revision_to: <gen_id>, model_diff_digest: "sha256:..." }`.
- A non-`draft` Job yields `PRECONDITION_FAILED`.

```python
env = await arch_learn_approve(repo_path, job_id=job_id)
# env["package_revision_to"], env["model_diff_digest"]
```

## The closed self-improvement loop

```
arch_mine ─▶ reservoir ─▶ arch_lessons (7 miners) ─▶ top lesson
                                                        │
                                                        ▼
                                                 arch_learn
                                                        │  (Job: draft)  ◀── gate
                                                        ▼
                                              arch_learn_approve
                                                        │  author → apply → publish
                                                        ▼
                                          new model generation
                                          (package_revision_to,
                                           model_diff_digest)
```

The `draft` state between `arch_learn` and `arch_learn_approve` is the approval
gate: no model change is authored or applied until you explicitly approve.

## Proposer configuration

`arch_learn_approve` authors the patch through a **proposer** plugin. Configure
it once per repo:

```yaml
# .architecture/ai/proposer_config.yaml
plugin: "opencode_arch.devloop.opencode_proposer:propose"
```

- Format: `plugin: "module.path:function_name"`.
- Plugin signature: `Callable[[WorkOrder], dict]` returning a ModelPatch
  `{"ops": [...]}`.
- The shipped proposer `opencode_arch.devloop.opencode_proposer:propose` asks a
  real OpenCode-backed LLM via `MCPProvider().structured`.

Resolution errors surface as `PRECONDITION_FAILED` with
`details.reason` one of: `no_proposer_configured`, `proposer_config_malformed`,
`proposer_plugin_not_loadable`, `proposer_plugin_not_callable`.

## Lesson signals (`arch_lessons`)

`arch_lessons` runs **7 signal miners** over your telemetry and builds a
`grounded_index` from verified promises. Two signals worth knowing:

- **`llm_calls`** — mined from `llm_calls.jsonl`.
- **`reservoir`** — contradiction signal, fires at threshold 2.

Call `arch_lessons` to inspect mined lessons and reviewable proposal stubs
before driving `arch_learn`.

## Running the end-to-end tests

```bash
cd /path/to/opencode-arch

# deterministic loop (runs by default)
python -m pytest tests/e2e/test_self_improvement_loop.py -q \
  --ignore=tests/logs_db/test_client.py

# opt-in real-OpenCode loop (requires OPENCODE_LIVE)
OPENCODE_LIVE=1 python -m pytest \
  tests/e2e/test_self_improvement_loop_opencode.py -q
```

The deterministic suite is 2 tests and needs no flags. The real-OpenCode suite
is gated by the `opencode_live` marker and the `OPENCODE_LIVE` environment
variable, so it is skipped unless explicitly enabled.
