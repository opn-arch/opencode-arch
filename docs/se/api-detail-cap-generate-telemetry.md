# API Detail — CAP-GENERATE: Code Generation & CAP-TELEMETRY: Telemetry & Metrics

---

## CAP-GENERATE: Code Generation

| Field | Value |
|-------|-------|
| ID | CAP-GENERATE |
| F-Block | F1 (Core Workflows) |
| Priority | High |
| Realized by | COMP-CLI (`cli/generate.py`) |
| Actor | Developer via CLI |

### Purpose

Regenerates code from an architecture model and validates via test suite. This is the single-shot version (vs. CAP-REGEN's iterative subsystem loop).

**Flow:** Load model → build generation prompt → run LLM → execute tests → report pass rate.

---

## CAP-TELEMETRY: Telemetry & Metrics

| Field | Value |
|-------|-------|
| ID | CAP-TELEMETRY |
| F-Block | F7 (Observability) |
| Priority | Medium |
| Realized by | COMP-TELEMETRY (`telemetry/store.py`) |
| Interface | IF-TELEMETRY (SQLite) |

---

### `TelemetryStore` — `opencode_arch.telemetry.store`

SQLite-backed persistent store at `~/.opencode-arch/telemetry.db`.

**Tables:**

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `invocations` | Tool call metrics | tool, repo, context_tokens, output_quality, iterations |
| `regen_outcomes` | Per-subsystem results | repo, subsystem, iteration, pass_rate, compression_ratio, mode |
| `learning_curve` | Per-repo aggregates | repo, repo_sequence, converged/total, avg_compression |
| `lessons` | Extracted insights | lesson_id (content-hash), category, description, evidence |
| `report_cards` | Run assessments | repo, mode, grade, fidelity, failure_patterns |
| `drift_flags` | Doc drift issues | file, issue, severity, auto_fixable, resolved |

---

### Primary Methods

#### Recording

| Method | Purpose |
|--------|---------|
| `record(tool, repo, context_tokens, output_quality, iterations, metadata)` | Log a tool invocation |
| `log_regen_outcome(repo, subsystem, iteration, ...)` | Log per-subsystem regen result |
| `record_learning_curve(repo, repo_sequence, mode, ...)` | Log per-repo aggregate |
| `record_report_card(repo, mode, grade, fidelity, ...)` | Store report card |
| `record_lesson(lesson_id, discovered_repo, category, description, evidence)` | Store deduped lesson |
| `record_drift_flag(file, issue, severity, auto_fixable, suggested_fix)` | Flag doc drift |

#### Querying

| Method | Returns |
|--------|---------|
| `query(tool=None, repo=None, limit=100)` | List of invocation dicts |
| `averages(tool=None)` | Aggregate stats (avg tokens, quality, iterations) |
| `get_patterns(repo=None)` | Historical failure patterns |
| `query_regen_outcomes(repo=None, subsystem=None)` | Regen outcome records |
| `get_learning_curve(mode=None)` | Learning curve data points |
| `get_report_cards(repo=None)` | Report cards |
| `get_lessons(category=None)` | Stored lessons |
| `mark_lesson_applied(lesson_id, repo)` | Track lesson application |
| `get_drift_flags(resolved=False)` | Outstanding drift flags |
| `resolve_drift_flag(flag_id)` | Mark flag resolved |

---

## Runner Backend (F6)

### `RunnerBackend` (Protocol) — `opencode_arch.runner.base`

```python
class RunnerBackend(Protocol):
    async def run(self, prompt: str, repo_path: str) -> RunResult: ...
```

### `RunResult` (dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `output` | `str` | Agent's text output |
| `exit_code` | `int` | Process exit code |
| `success` | `bool` | True if exit_code == 0 |

### `OpencodeRunner` — `opencode_arch.runner.opencode`

Concrete implementation invoking `opencode run` as subprocess.

```python
OpencodeRunner(timeout: int = 600, model: str | None = None)
```

**Behavior:**
- Passes prompt via stdin (avoids ARG_MAX limits)
- Sets `cwd=repo_path` (no `--dir` flag)
- Strips ANSI escape codes from output
- Returns `RunResult(success=False)` on timeout, missing binary, or exception
- Constrained by CON-TIMEOUT (600s default)

---

## CLI Commands (IF-CLI)

| Command | Capability | Handler |
|---------|-----------|---------|
| `opencode-arch extract <repo>` | CAP-EXTRACT | `cli/extract.py` |
| `opencode-arch generate <repo>` | CAP-GENERATE | `cli/generate.py` |
| `opencode-arch regen-loop --repo <path>` | CAP-REGEN | `cli/regen_loop.py` |
| `opencode-arch docs generate` | CAP-DOCS | `cli/docs.py` |
| `opencode-arch docs list` | CAP-DOCS | `cli/docs.py` |
| `opencode-arch metrics` | CAP-TELEMETRY | `cli/metrics.py` |
| `opencode-arch metrics --learning-curve` | CAP-TELEMETRY | `cli/metrics.py` |
| `opencode-arch metrics --drift` | CAP-TELEMETRY | `cli/metrics.py` |
| `opencode-arch report` | CAP-LEARN | `cli/metrics.py` |
| `opencode-arch bench` | CAP-REGEN | `cli/bench.py` |
