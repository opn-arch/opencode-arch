# Phase 2 Design: Oracle-First opencode-arch

> **Strategic insight:** Since opencode-arch runs as an MCP server inside OpenCode, the frontier model is already present — it's the agent itself. No separate oracle HTTP calls needed. Tools provide context; the agent does reasoning.

**Date:** 2026-07-06
**Status:** Approved
**Repo:** `opencode-arch`

---

## Core Principle

**Tools provide context. Agent does reasoning. No external model calls.**

The MCP tools are a "context compression engine" that makes the agent (frontier model) maximally effective with minimal tokens. The learning loop optimizes what context the tools provide.

## Token Arbitrage Goal

| Path | Tokens | Cost | When |
|------|--------|------|------|
| Full OpenCode workflow | 10K+ | High | Escalation / reviews only |
| Oracle mode (optimized context) | ~430 | Low | Default for all operations |
| Surrogate (future) | 0 API | Free | After oracle is excellent |

## Architecture

```
User Request → MCP Tool
                 │
                 ▼
         ┌──────────────┐
         │ architect_    │ → Returns OPTIMIZED CONTEXT to agent
         │ scan/slice    │    (~430 tokens instead of full repo)
         └──────┬───────┘
                │
                ▼
        Agent reasons with
        compressed context
                │
                ▼
         ┌──────────────┐
         │ architect_    │ → Validates agent's output
         │ validate      │ → Records telemetry
         └──────┬───────┘
                │
       confidence check
                │
      ┌─────────┴──────────┐
      ▼                    ▼
 HIGH confidence        LOW confidence
      │                    │
      ▼                    ▼
 Return result         ESCALATION
 + log telemetry       Full workflow (skill-guided iteration)
                       Records output for oracle learning
```

## Tool Set (5 tools)

| Tool | Input | Output | Role |
|------|-------|--------|------|
| `architect_scan` | repo_path | Manifest JSON | Raw AST inventory |
| `architect_slice` | manifest, focus, budget | Compressed context string | Token broker |
| `architect_validate` | model_yaml | {score, issues} | Quality gate |
| `architect_extract` | repo_path, model_yaml | Stored result + telemetry | Persistence |
| `architect_generate` | repo_path, model_yaml | Test results + files | Code quality gate |

## Learning Loop

```
telemetry DB records per invocation:
  - context_tokens_provided
  - output_quality (validation score)
  - iterations_needed (1 = oracle succeeded)
  - total_session_tokens

optimizer (offline, between sessions):
  - analyzes: "what budget produces first-try success?"
  - evolves: default budgets per repo pattern
  - curates: best (context, output) pairs as few-shot examples
```

## Deployment

```bash
pip install opencode-arch
```

Extension registered via opencode.json:
```json
{
  "name": "opencode-arch",
  "version": "0.2.0",
  "mcp": {
    "command": "python",
    "args": ["-m", "opencode_arch.mcp.server"]
  },
  "skills": ["skills/extraction", "skills/generation"]
}
```

## What Changes from Phase 1

| Remove | Add | Rewrite |
|--------|-----|---------|
| oracle/copilot_relay.py | context/slicer.py | mcp/tools/extract.py |
| oracle/__init__.py | context/budget.py | mcp/server.py |
| aiohttp dependency | context/examples.py | skills/extraction/SKILL.md |
| test_oracle.py | telemetry/store.py | pyproject.toml |
| | telemetry/recorder.py | |
| | mcp/tools/scan.py | |
| | mcp/tools/slice.py | |
| | mcp/tools/generate.py | |
| | skills/generation/SKILL.md | |
| | opencode.json | |
