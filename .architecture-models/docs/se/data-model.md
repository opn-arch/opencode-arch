---
document: Data Model
system: System
system_id: SYS-unknown
generated_at: 2026-08-18T20:07:47Z
generator_version: 0.3.0
model_hash: ceee27c08922
edition: 3
---

> **Model Completeness: F (0%)**
> Some sections may be empty due to missing model entities.
> - 56/56 components have no behavioral specification
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Data Model: System

## Data Components

### Src (artifacts) (COMP-3-1)
**Files:** `src/opencode_arch/artifacts/__init__.py`, `src/opencode_arch/artifacts/context.py`, `src/opencode_arch/artifacts/diagrams.py`, `src/opencode_arch/artifacts/selector.py`, `src/opencode_arch/artifacts/templates.py`

### LLM Prompt Relay (COMP-3-2)
**Files:** `src/opencode_arch/llm/cache.py`, `src/opencode_arch/llm/prompts/audit.py`, `src/opencode_arch/llm/prompts/matching.py`, `src/opencode_arch/llm/prompts/requirements.py`, `src/opencode_arch/llm/relay.py`

### Src (context) (COMP-3-3)
**Files:** `src/opencode_arch/context/__init__.py`, `src/opencode_arch/context/formatter.py`, `src/opencode_arch/context/pipeline_bridge.py`

### Src (learning) (COMP-3-4)
**Files:** `src/opencode_arch/learning/__init__.py`, `src/opencode_arch/learning/adapter.py`, `src/opencode_arch/learning/assessor.py`, `src/opencode_arch/learning/classifier.py`, `src/opencode_arch/learning/lessons.py`

### Src (runner) (COMP-3-5)
**Files:** `src/opencode_arch/runner/base.py`, `src/opencode_arch/runner/opencode.py`

### Src (agent) (COMP-3-6)
**Files:** `src/opencode_arch/agent/resolution.py`

### MCP Quality Server (COMP-3-7)
**Files:** `src/opencode_arch/mcp/__main__.py`, `src/opencode_arch/mcp/quality.py`, `src/opencode_arch/mcp/server.py`, `src/opencode_arch/mcp/tools/assess.py`, `src/opencode_arch/mcp/tools/author.py`

### Src (requirements) (COMP-3-8)
**Files:** `src/opencode_arch/requirements/llm_extractor.py`, `src/opencode_arch/requirements/matcher.py`, `src/opencode_arch/requirements/parser.py`, `src/opencode_arch/requirements/retroactive.py`

### CLI Commands (COMP-3-9)
**Files:** `src/opencode_arch/cli/bench.py`, `src/opencode_arch/cli/calibrate.py`, `src/opencode_arch/cli/confidence.py`, `src/opencode_arch/cli/docs.py`, `src/opencode_arch/cli/docs_validator.py`

### Src (prompts) (COMP-3-10)
**Files:** `src/opencode_arch/prompts/regen.py`

### Src (extract) (COMP-3-11)
**Files:** `src/opencode_arch/extract/__init__.py`

### Src (telemetry) (COMP-3-12)
**Files:** `src/opencode_arch/telemetry/collector.py`, `src/opencode_arch/telemetry/recorder.py`, `src/opencode_arch/telemetry/store.py`

### Src (regen) (COMP-3-13)
**Files:** `src/opencode_arch/regen/self_heal.py`, `src/opencode_arch/regen/spot_check.py`

