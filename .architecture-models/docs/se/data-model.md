---
document: Data Model
system: System
system_id: SYS-unknown
generated_at: 2026-08-18T23:31:29Z
generator_version: 0.3.0
model_hash: efca59bc201d
edition: 5
---

> **Model Completeness: F (0%)**
> Some sections may be empty due to missing model entities.
> - 57/57 components have no behavioral specification
> - No interfaces defined on components → interface-spec doc empty
> - No requirements defined
> - Actors defined but missing goals/descriptions
> Run the extraction pipeline or manually add behaviors/interfaces/constraints.

# Data Model: System
## Data Components
### Src (artifacts) (COMP-3-1)
**Files:** `src/opencode_arch/artifacts/__init__.py`, `src/opencode_arch/artifacts/context.py`, `src/opencode_arch/artifacts/diagrams.py`, `src/opencode_arch/artifacts/selector.py`, `src/opencode_arch/artifacts/templates.py`

### Src (llm) (COMP-3-2)
**Files:** `src/opencode_arch/llm/cache.py`, `src/opencode_arch/llm/prompts/audit.py`, `src/opencode_arch/llm/prompts/matching.py`, `src/opencode_arch/llm/prompts/requirements.py`, `src/opencode_arch/llm/relay.py`

### Src (context) (COMP-3-3)
**Files:** `src/opencode_arch/context/__init__.py`, `src/opencode_arch/context/formatter.py`, `src/opencode_arch/context/pipeline_bridge.py`

### Src (learning) (COMP-3-4)
**Files:** `src/opencode_arch/learning/__init__.py`, `src/opencode_arch/learning/adapter.py`, `src/opencode_arch/learning/assessor.py`, `src/opencode_arch/learning/classifier.py`, `src/opencode_arch/learning/lessons.py`

### Src (runner) (COMP-3-5)
**Files:** `src/opencode_arch/runner/base.py`, `src/opencode_arch/runner/opencode.py`

### Src (agent) (COMP-3-6)
**Files:** `src/opencode_arch/agent/resolution.py`

### Src (mcp) (COMP-3-7)
**Files:** `src/opencode_arch/mcp/__main__.py`, `src/opencode_arch/mcp/quality.py`, `src/opencode_arch/mcp/server.py`, `src/opencode_arch/mcp/tools/assess.py`, `src/opencode_arch/mcp/tools/author.py`

### Src (requirements) (COMP-3-8)
**Files:** `src/opencode_arch/requirements/llm_extractor.py`, `src/opencode_arch/requirements/matcher.py`, `src/opencode_arch/requirements/parser.py`, `src/opencode_arch/requirements/retroactive.py`

### Src (cli) (COMP-3-9)
**Files:** `src/opencode_arch/cli/bench.py`, `src/opencode_arch/cli/calibrate.py`, `src/opencode_arch/cli/confidence.py`, `src/opencode_arch/cli/docs.py`, `src/opencode_arch/cli/docs_validator.py`

### Src (prompts) (COMP-3-10)
**Files:** `src/opencode_arch/prompts/regen.py`

### Src (extract) (COMP-3-11)
**Files:** `src/opencode_arch/extract/__init__.py`

### Src (telemetry) (COMP-3-12)
**Files:** `src/opencode_arch/telemetry/collector.py`, `src/opencode_arch/telemetry/recorder.py`, `src/opencode_arch/telemetry/store.py`

### Src (regen) (COMP-3-13)
**Files:** `src/opencode_arch/regen/self_heal.py`, `src/opencode_arch/regen/spot_check.py`

---

---

## LLM Review

*Reviewed: 2026-08-18T23:31:57.798259+00:00 | Duration: 6412ms*

**Summary:** This data model document is essentially empty of meaningful architectural content—it lists source file groupings but provides no actual data model information such as entities, relationships, schemas, or data flows, rendering it ineffective as an architecture artifact.

- The document is labeled "Data Model" but contains no data entities, attributes, relationships, or schemas; it merely lists component file paths, which belongs in a component inventory, not a data model document.
- The 0% model completeness score with 57/57 components lacking behavioral specification confirms this is a scaffold with no substantive content, providing no architectural value in its current state.

<details>
<summary>Review details</summary>

**Prompt sent (truncated):**
```
Review the following architecture artifact 'docs/se/data-model.md'.
Respond ONLY in this format:
SUMMARY: <one paragraph overall assessment>
COMMENT: <specific observation>
COMMENT: <another observation>

---
---
document: Data Model
system: System
system_id: SYS-unknown
generated_at: 2026-08-18T23:31:29Z
generator_version: 0.3.0
model_hash: efca59bc201d
edition: 5
---

> **Model Completeness: F (0%)**
> Some sections may be empty due to missing model entities.
> - 57/57 components have no behav
```

**Full LLM response:**
```
SUMMARY: This data model document is essentially empty of meaningful architectural content—it lists source file groupings but provides no actual data model information such as entities, relationships, schemas, or data flows, rendering it ineffective as an architecture artifact.

COMMENT: The document is labeled "Data Model" but contains no data entities, attributes, relationships, or schemas; it merely lists component file paths, which belongs in a component inventory, not a data model document.

COMMENT: The 0% model completeness score with 57/57 components lacking behavioral specification confirms this is a scaffold with no substantive content, providing no architectural value in its current state.
```

</details>
