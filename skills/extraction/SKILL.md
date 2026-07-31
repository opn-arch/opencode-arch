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

## Escalation (Full Workflow)

If initial extraction scores below 60:
- Re-scan with narrower focus
- Increase budget: `architect_slice(repo_path, budget=8000, detail="full")`
- Extract one layer at a time, then merge

## Notes

- Smaller budget = cheaper but less context = may need more iterations
- First extraction of a repo usually needs higher budget (~4000)
- Subsequent refinements can use lower budget (~1000) focusing on specific areas
