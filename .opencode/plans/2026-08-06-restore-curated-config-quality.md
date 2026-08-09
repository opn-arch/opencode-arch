# Restore Curated Config & Fix Output Quality

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restore the old hand-curated `.architecture-model.yaml` config in logs_db, make `full_extraction()` respect curated config when present, fix behavior noise/capability naming/component naming, restore F7 function specs, and regenerate high-quality output.

**Architecture:** When a curated `.architecture-model.yaml` config exists with `functional_blocks:` and `layers:`, the pipeline should use those as component groupings and capability names instead of auto-generating generic ones. Behavior creation should filter to meaningful behaviors (~20-40, not 278). Capability naming should use block names from config, not naive URL parsing.

**Tech Stack:** Python 3.12, architecture-model-standard library, pytest

**Test command:** `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py --ignore=tests/test_docs_gen.py` (run from architecture-model-standard root)

**Pre-existing test count:** 971 passed, 97 skipped (architecture-model-standard)

---

## Context: What Was Better

The old output had:
- **9 domain-meaningful components**: "Core Domain Models", "LLM Pipeline Services", "Document and Code Intelligence" (vs generic "Models", "Services", "Extractors")
- **28 curated behaviors** (vs 278 noisy ones — one per function)
- **V&V function specs** (F7.1, F7.5) with decomposition, requirements, failure modes, test cases
- **Rich capabilities** matching functional blocks: "Ingest Source Data", "Enrich Log Entities", etc. (vs "Artifact Patche Management", "Processe Management")

The old `.architecture-model.yaml` config (103 lines, commit `8f2a22b`) defined 6 functional blocks (F1-F6) with domain-meaningful names and explicit file/dir mappings.

## Key Files

**architecture-model-standard** (`/Users/baigm2/Documents/Projects/architecture-model-standard/`):
- `src/architecture_model/orchestration/full_extraction.py` — main pipeline (lines 22-154)
- `src/architecture_model/orchestration/auto_enrich.py` — behavior creation (line 657, noise source)
- `src/architecture_model/orchestration/capability_inference.py` — capability naming (line 18, `_name_from_prefix`)
- `src/architecture_model/manifest/grouping.py` — component grouping (line 384, `create_components_from_manifest`)
- `src/architecture_model/orchestration/compaction.py` — model compaction (line 18)
- `src/architecture_model/config/schema.py` — `ProjectConfig`, `FunctionalBlockConfig` (line 62)
- `src/architecture_model/config/loader.py` — `get_config()` (line 104)

**logs_db** (`/Users/baigm2/Documents/Projects/logs_db/`):
- `.architecture-model.yaml` — currently the auto-extracted compact model (2458 lines, bad quality). Needs to be replaced with the old curated config (103 lines, from git `8f2a22b`)
- `.architecture-models/` — currently 45 auto-generated files (bad quality). Will be regenerated.
- `docs/architecture/` — old agent-curated docs (good quality, 9 components). Reference.
- `output/logs-db/architecture-model.yaml` — old v0.1 model (1532 lines, has actors + capabilities matching F-blocks)
- `.architecture-models/functions/F7/F7.1.yaml`, `F7.5.yaml` — committed in git at `00f4349`, deleted from working tree

---

### Task 1: Restore Old Config in logs_db

**Files:**
- Restore: `logs_db/.architecture-model.yaml` from git commit `8f2a22b`
- Restore: `logs_db/.architecture-models/functions/F7/F7.1.yaml` and `F7.5.yaml` from git HEAD
- Remove: `logs_db/.architecture-models/` (current 45 bad-quality files)

**Step 1: Remove current bad output**
```bash
cd /Users/baigm2/Documents/Projects/logs_db
rm -rf .architecture-models/COMP-* .architecture-models/docs .architecture-models/full-model.yaml
```

**Step 2: Restore the old curated config**
```bash
cd /Users/baigm2/Documents/Projects/logs_db
git show 8f2a22b:.architecture-model.yaml > .architecture-model.yaml
```

**Step 3: Restore F7 function specs**
```bash
cd /Users/baigm2/Documents/Projects/logs_db
git checkout HEAD -- .architecture-models/functions/F7/F7.1.yaml .architecture-models/functions/F7/F7.5.yaml
```

**Step 4: Verify**
```bash
head -10 .architecture-model.yaml  # Should show "project: name: logs-db, system: Knowledge OS"
ls .architecture-models/functions/F7/  # Should show F7.1.yaml, F7.5.yaml
```

---

### Task 2: Config-Aware Component Creation

Make `full_extraction()` read the curated config and use its functional blocks as component definitions when present. This replaces generic directory-based grouping with domain-meaningful names.

**Files:**
- Modify: `src/architecture_model/orchestration/full_extraction.py` (lines 22-96)
- Test: `tests/test_full_extraction.py` (new test)

**Step 1: Write the failing test**

```python
# tests/test_full_extraction.py — add to existing or create new
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from architecture_model.orchestration.full_extraction import full_extraction


def _make_config_with_blocks():
    """Create a ProjectConfig with functional blocks."""
    from architecture_model.config.schema import ProjectConfig, FunctionalBlockConfig
    return ProjectConfig(
        name="test-project",
        functional_blocks=[
            FunctionalBlockConfig(id="F1", name="Ingest Source Data", dirs=["scripts/ingestion"], files=["scripts/_pipeline_ingest.py"]),
            FunctionalBlockConfig(id="F2", name="Enrich Log Entities", files=["scripts/llm_enrich.py", "scripts/ontology_enrich.py"]),
        ],
    )


def test_full_extraction_uses_config_blocks(tmp_path):
    """When a curated config with functional_blocks exists, components should use block names."""
    # Create a minimal Python file for manifest to find
    (tmp_path / "scripts" / "ingestion").mkdir(parents=True)
    (tmp_path / "scripts" / "ingestion" / "ingest.py").write_text("def run(): pass")
    (tmp_path / "scripts" / "llm_enrich.py").write_text("def enrich(): pass")
    (tmp_path / "scripts" / "ontology_enrich.py").write_text("def classify(): pass")

    config = _make_config_with_blocks()

    with patch("architecture_model.orchestration.full_extraction.get_config", return_value=config):
        model = full_extraction(tmp_path)

    comp_names = {c.name for c in model.entities.components}
    assert "Ingest Source Data" in comp_names
    assert "Enrich Log Entities" in comp_names
```

**Step 2: Run test to verify it fails**
```bash
/opt/anaconda3/bin/python -m pytest tests/test_full_extraction.py::test_full_extraction_uses_config_blocks -v
```
Expected: FAIL (no `get_config` import in full_extraction.py)

**Step 3: Implement config-aware component creation in `full_extraction.py`**

Add after line 62 (imports section):
```python
from architecture_model.config.loader import get_config
```

Replace Step 3 (lines 81-95) with:
```python
    # Step 3: Group modules into components
    # Priority: curated config > SourceGraph > manifest grouping
    config = get_config(repo_path)
    
    if config.functional_blocks:
        # Config-aware path: use curated functional blocks as components
        components = _components_from_config(config, manifest, source_graph)
    elif multi_language and source_graph and len(source_graph.units) > len(manifest.modules):
        groups = group_source_graph(source_graph)
        components = []
        for i, g in enumerate(groups, 1):
            components.append(Component(
                id=f"COMP-{i}",
                name=g.name,
                status="ACTIVE",
                files=list(g.modules),
            ))
    else:
        components = create_components_from_manifest(manifest)
```

Add helper function before `full_extraction()`:
```python
def _components_from_config(config, manifest, source_graph=None):
    """Create components from curated config functional blocks.
    
    Each functional block becomes a component. Files are assigned by:
    1. Explicit file list from config block
    2. Directory membership from config block dirs
    3. Remaining files go to a catch-all component
    """
    from architecture_model.core.types import Component
    
    # Collect all known source files
    all_files = {m.file for m in manifest.modules}
    if source_graph:
        all_files |= {u.file for u in source_graph.units}
    
    components = []
    assigned = set()
    
    for i, block in enumerate(config.functional_blocks, 1):
        block_files = set()
        
        # Explicit files
        for f in block.files:
            if f in all_files:
                block_files.add(f)
        
        # Directory membership
        for d in block.dirs:
            for f in all_files:
                if f.startswith(d + "/") or f.startswith(d + "\\"):
                    block_files.add(f)
        
        assigned |= block_files
        components.append(Component(
            id=f"COMP-{i}",
            name=block.name,
            status="ACTIVE",
            files=sorted(block_files),
            source_block=block.id,
        ))
    
    # Remaining unassigned files → auto-group
    remaining = all_files - assigned
    if remaining:
        # Use existing grouping for unassigned files only
        from architecture_model.manifest.grouping import group_modules
        remaining_modules = [m for m in manifest.modules if m.file in remaining]
        if remaining_modules:
            interfaces = getattr(manifest, 'interfaces', []) or []
            groups = group_modules(remaining_modules, interfaces)
            for g in groups:
                i = len(components) + 1
                components.append(Component(
                    id=f"COMP-{i}",
                    name=g.name,
                    status="ACTIVE",
                    files=sorted(g.modules),
                ))
    
    return components
```

**Step 4: Run test to verify it passes**
```bash
/opt/anaconda3/bin/python -m pytest tests/test_full_extraction.py::test_full_extraction_uses_config_blocks -v
```

**Step 5: Run full test suite to check for regressions**
```bash
/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py --ignore=tests/test_docs_gen.py -x
```

**Step 6: Commit**
```bash
git add -A && git commit -m "feat: full_extraction uses curated config functional_blocks as components"
```

---

### Task 3: Config-Aware Capability Naming

When config has functional blocks, use their names as capabilities instead of inferring from URL prefixes.

**Files:**
- Modify: `src/architecture_model/orchestration/capability_inference.py` (lines 24-104)
- Test: `tests/test_capability_inference.py` (add test)

**Step 1: Write the failing test**

```python
def test_infer_capabilities_uses_config_block_names():
    """When components have source_block and config has block names, use those."""
    from architecture_model.orchestration.capability_inference import infer_capabilities
    from architecture_model.core.types import (
        ArchitectureModel, Entities, ModelMeta, Component, Behavior, Relationship, RelationType
    )
    
    model = ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(
            components=[
                Component(id="COMP-1", name="Ingest Source Data", status="ACTIVE", source_block="F1"),
                Component(id="COMP-2", name="Enrich Log Entities", status="ACTIVE", source_block="F2"),
            ],
            behaviors=[
                Behavior(id="BEH-1", name="run_ingest", status="ACTIVE", trigger="internal service call"),
                Behavior(id="BEH-2", name="enrich_log", status="ACTIVE", trigger="internal service call"),
            ],
        ),
        relationships=[
            Relationship(type=RelationType.REALIZES, from_id="COMP-1", to_id="BEH-1"),
            Relationship(type=RelationType.REALIZES, from_id="COMP-2", to_id="BEH-2"),
        ],
    )
    
    result = infer_capabilities(model)
    cap_names = {c.name for c in result.entities.capabilities}
    
    # Should use component names (from config blocks), NOT "Internal Operations"
    assert "Ingest Source Data" in cap_names
    assert "Enrich Log Entities" in cap_names
    assert "Internal Operations" not in cap_names
```

**Step 2: Run test to verify it fails**

**Step 3: Modify `infer_capabilities()` in `capability_inference.py`**

Add a new path at the top of `infer_capabilities()` (after line 38):
```python
    # If components have source_block assignments, derive capabilities from component names
    components = model.entities.components or []
    comp_has_blocks = any(getattr(c, 'source_block', None) for c in components)
    
    if comp_has_blocks:
        return _capabilities_from_component_blocks(model, behaviors, existing_caps, existing_rels)
```

Add helper:
```python
def _capabilities_from_component_blocks(model, behaviors, existing_caps, existing_rels):
    """Derive capabilities from component source_block names.
    
    Each component with a source_block gets a capability named after the component.
    Behaviors are assigned to capabilities via their component's realizes relationships.
    """
    components = model.entities.components or []
    comp_map = {c.id: c for c in components}
    
    # Map behaviors to their component via realizes relationships
    beh_to_comp = {}
    for r in model.relationships:
        rtype = r.type.value if hasattr(r.type, 'value') else str(r.type)
        if rtype == 'realizes' and r.from_id.startswith("COMP-"):
            beh_to_comp[r.to_id] = r.from_id
    
    new_caps = []
    new_rels = []
    cap_counter = len(existing_caps) + 1
    
    # One capability per component with source_block
    comp_to_cap = {}
    for comp in components:
        if getattr(comp, 'source_block', None):
            cap_id = f"CAP-{cap_counter}"
            cap = Capability(id=cap_id, name=comp.name, status="ACTIVE")
            new_caps.append(cap)
            comp_to_cap[comp.id] = cap_id
            cap_counter += 1
    
    # Assign behaviors to their component's capability
    ungrouped = []
    for beh in behaviors:
        comp_id = beh_to_comp.get(beh.id)
        cap_id = comp_to_cap.get(comp_id) if comp_id else None
        if cap_id:
            new_rels.append(Relationship(
                type=RelationType.REALIZES, from_id=beh.id, to_id=cap_id
            ))
        else:
            ungrouped.append(beh)
    
    # Ungrouped behaviors go to "Internal Operations" only if there are any
    if ungrouped:
        cap_id = f"CAP-{cap_counter}"
        new_caps.append(Capability(id=cap_id, name="Internal Operations", status="ACTIVE"))
        for beh in ungrouped:
            new_rels.append(Relationship(
                type=RelationType.REALIZES, from_id=beh.id, to_id=cap_id
            ))
    
    # Rebuild model
    new_entities = Entities(
        components=model.entities.components,
        capabilities=existing_caps + new_caps,
        behaviors=behaviors,
        constraints=model.entities.constraints,
        interfaces=model.entities.interfaces,
        layers=model.entities.layers,
        actors=model.entities.actors,
        systems=model.entities.systems,
        data=model.entities.data,
        events=model.entities.events,
        resources=model.entities.resources,
        environments=model.entities.environments,
        quality_attributes=model.entities.quality_attributes,
        decisions=model.entities.decisions,
        lifecycles=model.entities.lifecycles,
        requirements=model.entities.requirements,
    )
    return ArchitectureModel(
        meta=model.meta,
        entities=new_entities,
        relationships=existing_rels + new_rels,
    )
```

**Step 4: Run test, verify pass**

**Step 5: Also fix the `_name_from_prefix` typo bug** — replace `rstrip("s")` with proper singularization:
```python
def _name_from_prefix(prefix: str) -> str:
    """Convert URL prefix to capability name: 'users' -> 'User Management'."""
    # Don't strip 's' from short words or words ending in 'ss', 'us', 'is'
    word = prefix.replace('_', ' ').replace('-', ' ')
    if word.endswith("ies") and len(word) > 4:
        word = word[:-3] + "y"
    elif word.endswith("ses") or word.endswith("xes") or word.endswith("zes"):
        word = word[:-2]
    elif word.endswith("s") and not word.endswith(("ss", "us", "is")) and len(word) > 3:
        word = word[:-1]
    return f"{word.title()} Management"
```

**Step 6: Commit**
```bash
git add -A && git commit -m "feat: config-aware capability naming + fix singularization"
```

---

### Task 4: Behavior Filtering — Reduce Noise

Cut behaviors from 278 to ~20-40 meaningful ones. Two strategies:
1. **Significance filter**: only create behaviors for functions that are "significant" (have 3+ calls, or are router endpoints, or are entry points)
2. **CRUD collapse**: merge trivial CRUD functions (create/read/update/delete for same entity) into single behaviors

**Files:**
- Modify: `src/architecture_model/orchestration/auto_enrich.py` (line 657+)
- Test: `tests/test_auto_enrich.py`

**Step 1: Write the failing test**

```python
def test_behavior_filtering_skips_trivial_functions():
    """Functions with 0-1 calls and no router decorator should not become behaviors."""
    # Create a manifest with a mix of trivial and significant functions
    # ... (mock manifest with 20 functions, 5 significant, 15 trivial)
    # Assert: only ~5 behaviors created, not 20
```

**Step 2: Run test to verify it fails**

**Step 3: Modify `create_behaviors_from_manifest()` (line 707+)**

Add significance filter after line 712 (skip private functions):
```python
            # Skip trivial functions (fewer than 2 outgoing calls and not a router endpoint)
            call_count = len(func.calls) if hasattr(func, 'calls') and func.calls else 0
            if not is_router and call_count < 2:
                continue
            
            # Skip very short functions (likely utility/helper)
            line_count = getattr(func, 'line_count', 0) or 0
            if line_count > 0 and line_count < 5 and call_count < 2:
                continue
```

Also add CRUD collapse: group `create_X`, `get_X`, `update_X`, `delete_X` into a single `X CRUD` behavior when all 4 exist for the same entity.

**Step 4: Run test, verify pass**

**Step 5: Run full suite**

**Step 6: Commit**
```bash
git add -A && git commit -m "feat: filter trivial behaviors, collapse CRUD noise"
```

---

### Task 5: Fix Compaction Summaries

Replace meaningless "CompName: N behaviors" with useful summaries.

**Files:**
- Modify: `src/architecture_model/orchestration/compaction.py` (line 44-54)
- Test: `tests/test_compaction.py`

**Step 1: Write the failing test**

```python
def test_compact_summary_names_are_descriptive():
    """Summary behavior names should describe the component's role, not just count."""
    # ... create model with component "Ingest Source Data" and 5 behaviors
    compact, offloaded = compact_for_storage(model)
    summary_behs = [b for b in compact.entities.behaviors if b.id.startswith("BEH-")]
    # Name should NOT be "Ingest Source Data: 5 behaviors"
    for b in summary_behs:
        assert ": " not in b.name or "behaviors" not in b.name
```

**Step 2: Implement** — change summary naming to use component name + "operations" and list top behavior names as description instead of steps:
```python
# Instead of: name = f"{comp_name}: {len(behs)} behaviors"
# Use: name = f"{comp_name} Operations"
# And: description = f"Includes: {', '.join(beh.name for beh in behs[:5])}"
```

**Step 3: Run tests, commit**

---

### Task 6: Generate Component-to-Component Relationships

The current output has zero component-to-component relationships, making ICD empty. Derive `depends-on` relationships from import analysis.

**Files:**
- Modify: `src/architecture_model/orchestration/full_extraction.py` (add step after Step 6)
- Test: `tests/test_full_extraction.py`

**Step 1: Write the failing test**

```python
def test_full_extraction_creates_component_dependencies():
    """Components should have depends-on relationships based on import edges."""
    # Create repo where router file imports from services file
    # Both assigned to different components
    # Assert: depends-on relationship exists from router component to service component
```

**Step 2: Implement** — add a new step after behavior creation:

```python
    # Step 6b: Derive component-to-component dependencies from imports
    comp_rels = _derive_component_dependencies(components, manifest)
    model = dc_replace(model, relationships=list(model.relationships) + comp_rels)
```

Helper function:
```python
def _derive_component_dependencies(components, manifest):
    """Create depends-on relationships between components based on import edges."""
    file_to_comp = {}
    for comp in components:
        for f in (comp.files or []):
            file_to_comp[f] = comp.id
    
    edges = set()
    for mod in manifest.modules:
        src_comp = file_to_comp.get(mod.file)
        if not src_comp:
            continue
        for imp in (mod.imports or []):
            # Try to resolve import to a file
            for other_mod in manifest.modules:
                if other_mod.name == imp or imp.startswith(other_mod.name + "."):
                    tgt_comp = file_to_comp.get(other_mod.file)
                    if tgt_comp and tgt_comp != src_comp:
                        edges.add((src_comp, tgt_comp))
    
    return [
        Relationship(type=RelationType.DEPENDS_ON, from_id=src, to_id=tgt)
        for src, tgt in edges
    ]
```

**Step 3: Run tests, commit**

---

### Task 7: Regenerate logs_db Output

Run the improved pipeline on logs_db and verify quality improvement.

**Step 1: Run extraction**
```python
from pathlib import Path
from architecture_model.orchestration.full_extraction import full_extraction_with_docs
model, paths = full_extraction_with_docs(Path("/Users/baigm2/Documents/Projects/logs_db"))
```

**Step 2: Verify quality checklist**
- [ ] Component names match functional blocks: "Ingest Source Data", "Enrich Log Entities", etc.
- [ ] Behavior count < 50 (was 278, old curated was 28)
- [ ] Capability names match block names, no typos
- [ ] ICD has component-to-component relationships (was empty)
- [ ] System design lists curated key behaviors, not all
- [ ] Component docs have descriptions (not "—")

**Step 3: Compare with `docs/architecture/` reference**
```bash
diff <(grep "^| " .architecture-models/docs/system-design.md) <(grep "^| " docs/architecture/system_design.md)
```

**Step 4: If quality is acceptable, commit the output**
```bash
cd /Users/baigm2/Documents/Projects/logs_db
git add .architecture-model.yaml .architecture-models/
git commit -m "feat: regenerate architecture output with curated config + quality fixes"
```

---

## Summary of Changes

| What | Before | After |
|------|--------|-------|
| Components | 8 generic ("Models", "Services") | 6+ domain-meaningful ("Ingest Source Data", "Serve API & UI") |
| Behaviors | 278 (one per function) | ~20-40 (significant only, CRUD collapsed) |
| Capabilities | 31 with typos + "Internal Operations" bucket | 6 matching functional blocks |
| Component relationships | 0 (empty ICD) | N depends-on edges from imports |
| Capability names | "Artifact Patche Management" | "Ingest Source Data" |
| Compaction | "CompName: 193 behaviors" | "CompName Operations" with description |
| F7 function specs | Deleted from working tree | Restored from git |
| Config | Auto-extracted compact model | Restored curated config with F1-F6 blocks |
