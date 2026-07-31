# API Detail — CAP-EXTRACT: Architecture Extraction

## Overview

| Field | Value |
|-------|-------|
| ID | CAP-EXTRACT |
| F-Block | F1 (Core Workflows) |
| Priority | High |
| Realized by | COMP-CLI (`cli/extract.py`) |
| Actor | Developer via CLI |
| Constraint | CON-NO-HALLUCINATION |

---

## Primary API

### `run_extract(repo_path, runner, budget=4000, focus="all", target_score=80) -> dict`

**Module:** `opencode_arch.cli.extract`

The full extraction loop. Orchestrates AST scanning → context compression → LLM inference → validation → persistence.

**Algorithm:**

1. Validate repo path exists
2. Format extraction prompt with `EXTRACT_PROMPT.format(repo_path, focus, budget, target_score)`
3. Call `runner.run(prompt, repo_path)` — sends prompt to OpenCode subprocess
4. Extract YAML from agent output (between ````yaml` fences or heuristic detection)
5. Call `store_extraction(repo_path, model_yaml, context_tokens)` to validate and persist
6. Return result metrics

**Return dict:**

| Key | Type | Description |
|-----|------|-------------|
| `success` | `bool` | Whether extraction produced a valid model |
| `score` | `int` | Validation score (0-100) |
| `tokens_used` | `int` | Context token budget used |
| `time_seconds` | `float` | Total elapsed time |
| `iterations` | `int` | Always 1 (single-shot extraction) |
| `issues` | `list[str]` | Validation issues found |
| `path` | `str` | Path where model was stored |
| `error` | `str` | Error message (if `success=False`) |

**Parameters:**

| Param | Default | Purpose |
|-------|---------|---------|
| `repo_path` | — | Absolute path to repo to extract |
| `runner` | — | `RunnerBackend` instance (OpencodeRunner) |
| `budget` | 4000 | Token budget for context compression |
| `focus` | `"all"` | `"all"`, F-block ID, or layer name |
| `target_score` | 80 | Minimum acceptable validation score |

---

## Supporting Functions

### `_extract_yaml_from_output(output: str) -> str | None`

Extracts YAML model content from LLM agent output. Tries three strategies:

1. ````yaml ... ``` `` fenced block
2. Generic ``` ``` `` block containing `meta:` or `entities:`
3. Unfenced `meta:\n...` block up to double-newline

Returns `None` if no YAML found (triggers error path).

---

## Behavioral View: BEH-EXTRACT

**Trigger:** `opencode-arch extract <repo> [--budget N] [--focus F] [--target-score N]`

**Sequence:**

```
Developer ──► CLI (extract)
                │
                ├─► Validate path
                ├─► Format EXTRACT_PROMPT
                ├─► runner.run(prompt, repo_path) ──► OpenCode subprocess
                │                                        │
                │   ◄── YAML model output ──────────────-│
                │
                ├─► _extract_yaml_from_output()
                ├─► store_extraction() ──► validate + write .architecture-model.yaml
                ├─► Record telemetry
                │
Developer ◄── result dict
```

**Postconditions:**
- `.architecture-model.yaml` written to repo root (if score >= target)
- Telemetry recorded
- No source code modified
