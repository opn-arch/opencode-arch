# Skill: Architecture Extraction

## When to Use

Use when the user asks to extract, document, or analyze the architecture of a codebase.

## Workflow

1. **Scan**: Call `architect_scan(repo_path)` to generate the reality manifest.
   - Review module count, metrics, functional blocks.
   - The scan now includes `suggested_components` with auto-grouped modules.

2. **Group** (optional): Call `architect_group(repo_path)` for detailed component groupings.
   - Returns named groups with file lists and primary files.
   - Uses multi-signal affinity: subdirectory, name-prefix, imports.
   - Use these as component boundaries in your extraction.

3. **Slice**: Call `architect_slice(repo_path, focus, budget=4000)` to get compressed context.
   - For large repos, start with focus on a specific layer or F-block.
   - Default budget of 4000 tokens is usually sufficient.
   - Fallback path now includes grouped component suggestions.

4. **Extract**: Using the context from the slice, produce a YAML architecture model following the 7-entity, 8-relationship schema:
   - Entities: capabilities, components, layers, behaviors, interfaces, constraints, actors
   - Relationships: realizes, uses, constrains, contains, triggers, depends_on, implements, exposes
   - Every entity needs: id, name, status (ACTIVE/PLANNED/DEPRECATED)
   - Every relationship needs: from, to, type

5. **Validate**: Call `architect_validate(model_yaml)` to check structural quality.
    - Target score: 80+
    - If score < 80: review issues, fix the model, re-validate.
    - Common issues: orphaned entities, dangling references, missing meta.

6. **Store**: Call `architect_extract(repo_path, model_yaml, context_tokens)` to persist.
    - Writes .architecture-model.yaml to the repo root.
    - Records telemetry for future optimization.
    - **Auto-generates**: SE docs, sub-models, recursive manifests, and granular behaviors.
    - Returns: `behaviors_created`, `sub_models`, `recursive_manifests`, `docs_generated`.

7. **Check**: Call `architect_check(repo_path, model_yaml)` to verify representativeness.
    - Target: 100% on all three sub-scores.
    - If file_coverage < 100%: add uncovered files to appropriate components.
    - If relationship_accuracy < 100%: verify unverified relationships or remove them.
    - If boundary_coherence < 100%: consider re-grouping low-coherence components.
    - Iterate until overall = 100%.

8. **Decompose** (optional): Call `architect_decompose(repo_path)` to re-run decomposition.
    - Useful after model corrections or re-extraction.
    - Produces per-F-block sub-models and recursive manifests.

9. **Docs** (optional): Call `architect_docs(repo_path)` to regenerate SE documentation.
    - Generates: component_specs, icd, dependency_matrix, health, index.
    - Drift report requires a previous model snapshot.

## Behaviors

The system auto-creates granular behaviors from the manifest (one per router/service function).
However, you should also produce **high-level behaviors** in your model for cross-component workflows:

```yaml
entities:
  behaviors:
    - id: BEH-1
      name: Log Processing Pipeline
      source_file: app/services/log_pipeline.py
      trigger: "POST /logs creates a new log"
      steps:
        - "Classify log type via LLM (log_classifier)"
        - "Extract action items (log_action_extractor)"
        - "Generate embedding for search (embedding_service)"
        - "Trigger artifact patch if relevant (artifact_patcher)"
      status: ACTIVE
    - id: BEH-2
      name: Semantic Search
      source_file: app/services/query_service.py
      trigger: "GET /search?q=..."
      steps:
        - "Embed query text"
        - "Vector similarity search via pgvector"
        - "Rank and return results"
      status: ACTIVE
```

Include behaviors for:
- Every significant API workflow (not just CRUD — focus on multi-step flows)
- Background pipelines and scheduled jobs
- Cross-component orchestration patterns

Link behaviors to components via relationships:
```yaml
relationships:
  - from: COMP-4
    to: BEH-1
    type: realizes
  - from: COMP-7
    to: BEH-1
    type: realizes
```

Note: Granular per-function behaviors are auto-generated after store. You only need to provide
the high-level architectural behaviors that span multiple components.

## Escalation (Full Workflow)

If initial extraction scores below 60:
- Re-scan with narrower focus
- Increase budget: `architect_slice(repo_path, budget=8000, detail="full")`
- Extract one layer at a time, then merge

## Notes

- Smaller budget = cheaper but less context = may need more iterations
- First extraction of a repo usually needs higher budget (~4000)
- Subsequent refinements can use lower budget (~1000) focusing on specific areas
