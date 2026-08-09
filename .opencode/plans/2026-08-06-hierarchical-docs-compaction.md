# Hierarchical Docs + Model Compaction Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make hierarchical documentation, model compaction, and use-case diagrams standard output of the extraction pipeline. The main `.architecture-model.yaml` should be compact (~50KB) with detail offloaded to sub-models and docs.

**Architecture:** Three layers of change: (1) Fix bugs preventing use-case inference and doc generation, (2) Wire missing doc generators + add use-case diagrams + create `diagrams.py`, (3) Add post-extraction compaction to `full_extraction()` and make the pipeline produce a complete `.architecture-models/` directory.

**Tech Stack:** Python 3.12, architecture-model-standard, opencode-arch, Mermaid diagrams.

**Repo:** Both repos. Primary: `architecture-model-standard` at `/Users/baigm2/Documents/Projects/architecture-model-standard/`, secondary: `opencode-arch` at `/Users/baigm2/Documents/Projects/opencode-arch/`

**Run tests:**
- arch-model-std: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py --ignore=tests/test_docs_gen.py`
- opencode-arch: `/opt/anaconda3/bin/python -m pytest tests/ -v`

**Key constraints:**
- `Relationship.type` can be string OR `RelationType` enum — always handle both when comparing
- `save_model()` requires enum types — convert strings before saving
- `generate_manifest()` only finds subdirectory files (known root-level bug)
- Existing tests must not regress

---

## Phase 1: Bug Fixes (architecture-model-standard)

### Task 1: Fix Relationship type comparison in use_case_inference.py

The `infer_composite_behaviors()` at line 50 does `r.type == "triggers"` which fails when `r.type` is `RelationType.TRIGGERS` (enum). This is why use cases aren't being created.

**Files:**
- Modify: `src/architecture_model/orchestration/use_case_inference.py:50`
- Test: `tests/test_use_case_inference.py` (add enum-type test)

**Step 1: Add test for enum-type triggers**

In `tests/test_use_case_inference.py`, add a test that passes `RelationType.TRIGGERS` enum values instead of strings:

```python
def test_infer_with_enum_relationship_types():
    """Use case inference works when relationships have enum types."""
    from architecture_model.core.types import RelationType
    # ... create model with RelationType.TRIGGERS relationships
    result = infer_composite_behaviors(model)
    ucs = [b for b in result.entities.behaviors if b.id.startswith("UC-")]
    assert len(ucs) >= 1
```

**Step 2: Fix the comparison**

In `use_case_inference.py` line 50, replace:
```python
triggers = [r for r in model.relationships if r.type == "triggers"]
```
with:
```python
def _is_trigger(r):
    t = r.type
    return (t == "triggers" or (hasattr(t, 'value') and t.value == "triggers"))

triggers = [r for r in model.relationships if _is_trigger(r)]
```

Also fix line 79 — relationship creation uses string `"contains"`, should use `RelationType`:
```python
new_rels.append(Relationship(type=RelationType.CONTAINS, from_id=composite.id, to_id=bid))
```

**Step 3: Set use-case pattern on composite behaviors**

Line 68-75 — the composite Behavior isn't getting `pattern="use-case"` set. Add it:
```python
composite = Behavior(
    id=f"UC-{i}",
    name=f"{head.name} (end-to-end)",
    status="ACTIVE",
    trigger=head.trigger,
    actor=head.actor,
    steps=[beh_index[bid].name for bid in chain if bid in beh_index],
    pattern="use-case",  # <-- ADD THIS
)
```

**Step 4: Run tests**

```bash
/opt/anaconda3/bin/python -m pytest tests/test_use_case_inference.py -v
```

---

### Task 2: Fix Relationship type normalization in full_extraction.py

The `full_extraction()` pipeline creates relationships with mixed string/enum types across different pipeline stages. Add a normalization pass at the end.

**Files:**
- Modify: `src/architecture_model/orchestration/full_extraction.py` (add normalization before return)

**Step 1: Add normalization helper**

At the end of `full_extraction()`, before `return model`, add:
```python
# Normalize relationship types to enums for save_model() compatibility
from architecture_model.core.types import RelationType
normalized_rels = []
for r in model.relationships:
    if isinstance(r.type, str):
        try:
            r = dc_replace(r, type=RelationType(r.type))
        except ValueError:
            pass  # keep string if not a known type
    normalized_rels.append(r)
model = dc_replace(model, relationships=normalized_rels)
```

**Step 2: Run tests**

```bash
/opt/anaconda3/bin/python -m pytest tests/test_full_extraction.py tests/test_use_case_inference.py -v
```

---

## Phase 2: Docs Infrastructure (architecture-model-standard)

### Task 3: Create docs/diagrams.py with Mermaid generators

Currently `docs/diagrams.py` doesn't exist — `generate_docs()` silently fails trying to import it.

**Files:**
- Create: `src/architecture_model/docs/diagrams.py`
- Test: `tests/test_diagrams.py`

**Step 1: Write tests**

```python
"""Tests for Mermaid diagram generation."""
from architecture_model.docs.diagrams import (
    generate_component_diagram,
    generate_use_case_diagram,
    generate_all_diagrams,
)

class TestComponentDiagram:
    def test_produces_mermaid_graph(self, model_with_deps):
        md = generate_component_diagram(model)
        assert "```mermaid" in md
        assert "graph TD" in md or "graph LR" in md

class TestUseCaseDiagram:
    def test_produces_sequence_diagram_per_use_case(self, model_with_use_cases):
        md = generate_use_case_diagram(model)
        assert "sequenceDiagram" in md

class TestGenerateAllDiagrams:
    def test_writes_files_to_output_dir(self, tmp_path, simple_model):
        paths = generate_all_diagrams(model, tmp_path)
        assert len(paths) >= 1
```

**Step 2: Implement diagrams.py**

```python
"""Mermaid diagram generators for architecture documentation."""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel


def _rel_type_str(rel_type) -> str:
    return rel_type.value if hasattr(rel_type, 'value') else str(rel_type)


def generate_component_diagram(model: "ArchitectureModel") -> str:
    """Generate Mermaid component dependency diagram."""
    lines = ["# Component Diagram", "", "```mermaid", "graph TD"]
    components = getattr(model.entities, 'components', []) or []
    comp_map = {c.id: c for c in components}
    
    # Add nodes
    for c in components:
        lines.append(f"  {c.id}[{c.name}]")
    
    # Add edges from depends-on/uses relationships
    for r in model.relationships:
        rt = _rel_type_str(r.type)
        if rt in ("depends-on", "uses") and r.from_id in comp_map and r.to_id in comp_map:
            lines.append(f"  {r.from_id} --> {r.to_id}")
    
    lines.extend(["```", ""])
    return "\n".join(lines)


def generate_use_case_diagram(model: "ArchitectureModel") -> str:
    """Generate Mermaid sequence diagrams for use cases (composite behaviors)."""
    lines = ["# Use Case Diagrams", ""]
    behaviors = getattr(model.entities, 'behaviors', []) or []
    use_cases = [b for b in behaviors if b.id.startswith("UC-")]
    
    if not use_cases:
        lines.append("No use cases found.")
        return "\n".join(lines)
    
    # Build behavior index for step lookup
    beh_index = {b.name: b for b in behaviors}
    
    # Build component mapping from realizes relationships
    beh_to_comp = {}
    for r in model.relationships:
        if _rel_type_str(r.type) == "realizes":
            beh_to_comp[r.to_id] = r.from_id
    comp_map = {c.id: c for c in (getattr(model.entities, 'components', []) or [])}
    
    for uc in use_cases:
        lines.append(f"## {uc.name}")
        lines.append(f"**Trigger:** {uc.trigger or 'N/A'}")
        lines.append(f"**Actor:** {uc.actor or 'System'}")
        lines.append("")
        lines.append("```mermaid")
        lines.append("sequenceDiagram")
        
        # Collect participants (components involved)
        participants = []
        step_comps = []
        for step_name in (uc.steps or []):
            step_beh = beh_index.get(step_name)
            if step_beh:
                comp_id = beh_to_comp.get(step_beh.id, "Unknown")
                comp_name = comp_map[comp_id].name if comp_id in comp_map else comp_id
            else:
                comp_name = "Unknown"
            step_comps.append(comp_name)
            if comp_name not in participants:
                participants.append(comp_name)
        
        for p in participants:
            lines.append(f"    participant {p}")
        
        # Draw messages between components
        prev = None
        for step_name, comp_name in zip(uc.steps or [], step_comps):
            if prev and prev != comp_name:
                lines.append(f"    {prev}->>+{comp_name}: {step_name}()")
            elif prev and prev == comp_name:
                lines.append(f"    Note over {comp_name}: {step_name}()")
            else:
                lines.append(f"    Note over {comp_name}: {step_name}()")
            prev = comp_name
        
        lines.extend(["```", ""])
    
    return "\n".join(lines)


def generate_system_boundary_diagram(model: "ArchitectureModel") -> str:
    """Generate Mermaid diagram showing system boundaries with components."""
    lines = ["# System Boundaries", "", "```mermaid", "graph TD"]
    systems = getattr(model.entities, 'systems', []) or []
    components = getattr(model.entities, 'components', []) or []
    comp_map = {c.id: c for c in components}
    
    for sys in systems:
        lines.append(f"  subgraph {sys.id}[{sys.name}]")
        for cid in (sys.component_ids or []):
            if cid in comp_map:
                lines.append(f"    {cid}[{comp_map[cid].name}]")
        lines.append("  end")
    
    # Orphan components (not in any system)
    sys_comps = {cid for s in systems for cid in (s.component_ids or [])}
    orphans = [c for c in components if c.id not in sys_comps]
    if orphans:
        for c in orphans:
            lines.append(f"  {c.id}[{c.name}]")
    
    lines.extend(["```", ""])
    return "\n".join(lines)


def generate_all_diagrams(model: "ArchitectureModel", output_dir: Path) -> list[Path]:
    """Generate all diagrams, write to output_dir, return paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    
    # Component diagram
    md = generate_component_diagram(model)
    p = output_dir / "component-diagram.md"
    p.write_text(md)
    paths.append(p)
    
    # Use case diagrams
    md = generate_use_case_diagram(model)
    p = output_dir / "use-case-diagrams.md"
    p.write_text(md)
    paths.append(p)
    
    # System boundary diagram
    systems = getattr(model.entities, 'systems', []) or []
    if systems:
        md = generate_system_boundary_diagram(model)
        p = output_dir / "system-boundaries.md"
        p.write_text(md)
        paths.append(p)
    
    return paths
```

**Step 3: Run tests**

```bash
/opt/anaconda3/bin/python -m pytest tests/test_diagrams.py -v
```

---

### Task 4: Wire missing generators into generate_docs()

The `generate_docs()` in `architecture-model-standard` is missing system_design, behavior specs, integration_flows, and use-case diagrams.

**Files:**
- Modify: `src/architecture_model/docs/generator.py`

**Step 1: Add system design**

After health report block, add:
```python
# System design
try:
    from architecture_model.docs.system_design import generate_system_design
    sd_md = generate_system_design(model, manifest)
    sd_path = output_dir / "system-design.md"
    sd_path.write_text(sd_md)
    result["system_design"] = [sd_path]
except Exception:
    pass
```

**Step 2: Add integration flows**

```python
# Integration flows
try:
    from architecture_model.docs.integration_flows import generate_integration_flows
    if_md = generate_integration_flows(model)
    if_path = output_dir / "integration-flows.md"
    if_path.write_text(if_md)
    result["integration_flows"] = [if_path]
except Exception:
    pass
```

**Step 3: Run tests**

```bash
/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py --ignore=tests/test_docs_gen.py -k "docs or diagram"
```

---

## Phase 3: Model Compaction + Hierarchical Output (architecture-model-standard)

### Task 5: Add compaction to full_extraction() pipeline

The main model is 310KB/15K lines. Add a `compact_model()` function that offloads detail to sub-models, keeping the main model under ~50KB.

**Files:**
- Create: `src/architecture_model/orchestration/compaction.py`
- Modify: `src/architecture_model/orchestration/full_extraction.py`
- Test: `tests/test_compaction.py`

**What gets offloaded:**
1. **Leaf behaviors** → kept in sub-models only. Main model keeps only use cases (UC-*) + CRUD summaries per component.
2. **Structured steps** → stripped from main model behaviors (kept in sub-models).
3. **Detailed preconditions/postconditions** → stripped from main model.

**What stays in main model:**
- All components (with files list)
- All systems
- All capabilities
- Use cases (composite behaviors, ~33)
- CRUD summary behaviors (1 per component, ~8)
- All inter-component relationships (realizes, depends-on, contains for UCs)

**Step 1: Write tests**

```python
"""Tests for model compaction."""
from architecture_model.orchestration.compaction import compact_for_storage

class TestCompaction:
    def test_reduces_behavior_count(self, full_model):
        compact, offloaded = compact_for_storage(full_model)
        assert len(compact.entities.behaviors) < len(full_model.entities.behaviors)
    
    def test_keeps_use_cases(self, full_model):
        compact, offloaded = compact_for_storage(full_model)
        uc_ids = {b.id for b in compact.entities.behaviors if b.id.startswith("UC-")}
        assert len(uc_ids) > 0
    
    def test_offloaded_contains_detail(self, full_model):
        compact, offloaded = compact_for_storage(full_model)
        assert len(offloaded) > 0  # dict of component_id -> sub-behaviors
    
    def test_preserves_components_and_systems(self, full_model):
        compact, offloaded = compact_for_storage(full_model)
        assert len(compact.entities.components) == len(full_model.entities.components)
        assert len(compact.entities.systems) == len(full_model.entities.systems)
```

**Step 2: Implement compaction.py**

```python
"""Model compaction — offload detail to sub-models."""
from __future__ import annotations
from dataclasses import replace as dc_replace
from architecture_model.core.types import (
    ArchitectureModel, Behavior, Entities, Relationship, RelationType
)

def compact_for_storage(model: ArchitectureModel) -> tuple[ArchitectureModel, dict[str, list[Behavior]]]:
    """Compact a model by offloading leaf behaviors to per-component groups.
    
    Returns:
        (compact_model, offloaded) where offloaded maps component_id -> list[Behavior]
    """
    behaviors = model.entities.behaviors or []
    
    # Separate use cases from leaf behaviors
    use_cases = [b for b in behaviors if b.id.startswith("UC-")]
    leaf_behaviors = [b for b in behaviors if not b.id.startswith("UC-")]
    
    # Build component mapping from realizes relationships
    beh_to_comp = {}
    for r in model.relationships:
        rt = r.type.value if hasattr(r.type, 'value') else str(r.type)
        if rt == "realizes":
            beh_to_comp[r.to_id] = r.from_id
    
    # Group leaf behaviors by component
    comp_behaviors: dict[str, list[Behavior]] = {}
    for beh in leaf_behaviors:
        comp_id = beh_to_comp.get(beh.id, "UNKNOWN")
        comp_behaviors.setdefault(comp_id, []).append(beh)
    
    # Create CRUD summary per component
    summary_behaviors = []
    for comp_id, behs in comp_behaviors.items():
        summary_behaviors.append(Behavior(
            id=f"BEH-SUMMARY-{comp_id}",
            name=f"{comp_id}: {len(behs)} behaviors",
            status="ACTIVE",
            trigger=f"{len(behs)} endpoints",
            steps=[b.name for b in behs[:10]],  # sample
        ))
    
    # Compact model: use cases + summaries only
    kept = use_cases + summary_behaviors
    kept_ids = {b.id for b in kept}
    
    # Filter relationships: keep non-behavior + kept behavior rels
    kept_rels = [
        r for r in model.relationships
        if not (r.to_id.startswith("BEH-") and r.to_id not in kept_ids)
    ]
    
    compact = dc_replace(
        model,
        entities=dc_replace(model.entities, behaviors=kept),
        relationships=kept_rels,
    )
    
    return compact, comp_behaviors
```

---

### Task 6: Add hierarchical output to full_extraction()

Make `full_extraction()` produce the complete `.architecture-models/` directory with docs, sub-models, and diagrams.

**Files:**
- Modify: `src/architecture_model/orchestration/full_extraction.py`

**Step 1: Add `full_extraction_with_docs()` function**

```python
def full_extraction_with_docs(
    repo_path: Path,
    target_systems: int = 0,
    output_dir: str = ".architecture-models",
) -> tuple[ArchitectureModel, dict]:
    """Full extraction + docs + compaction.
    
    Returns (compact_model, artifacts) where artifacts describes what was written.
    """
    # Run full extraction
    model = full_extraction(repo_path, target_systems=target_systems)
    
    # Normalize relationship types
    ...
    
    # Compact for storage
    compact, offloaded = compact_for_storage(model)
    
    # Write compact model
    save_model(compact, repo_path / ".architecture-model.yaml")
    
    # Write full model as reference
    save_model(model, repo_path / output_dir / "full-model.yaml")
    
    # Write per-component sub-models
    out = repo_path / output_dir
    for comp_id, behaviors in offloaded.items():
        comp_dir = out / comp_id
        comp_dir.mkdir(parents=True, exist_ok=True)
        # Build sub-model for this component
        ...
    
    # Generate docs
    from architecture_model.docs import generate_docs
    generate_docs(model, out / "docs", manifest=manifest)
    
    # Generate diagrams
    from architecture_model.docs.diagrams import generate_all_diagrams
    generate_all_diagrams(model, out / "docs" / "diagrams")
    
    return compact, artifacts
```

---

### Task 7: Run on logs_db and verify output

**Step 1: Run extraction**

```python
from pathlib import Path
from architecture_model.orchestration.full_extraction import full_extraction_with_docs

repo = Path("/Users/baigm2/Documents/Projects/logs_db")
compact, artifacts = full_extraction_with_docs(repo)
```

**Step 2: Verify output structure**

```
.architecture-model.yaml          (~50KB compact model)
.architecture-models/
├── full-model.yaml               (complete model for reference)
├── docs/
│   ├── README.md
│   ├── system-design.md
│   ├── components/COMP-*.md
│   ├── behaviors/index.md + BEH-*.md
│   ├── diagrams/
│   │   ├── component-diagram.md
│   │   ├── use-case-diagrams.md
│   │   └── system-boundaries.md
│   ├── dependency-matrix.md
│   ├── icd.md
│   ├── integration-flows.md
│   └── health.md
├── COMP-1/
│   └── .architecture-model.yaml  (sub-model with full behaviors)
├── COMP-2/
│   └── ...
```

**Step 3: Verify compact model size**

```bash
wc -l .architecture-model.yaml  # target: <2000 lines / <50KB
wc -l .architecture-models/full-model.yaml  # full: ~15K lines
```

---

## Phase 4: opencode-arch Integration

### Task 8: Update opencode-arch docs tool to use new generators

The opencode-arch `generate_docs()` tool already generates most doc types. It just needs to also generate use-case diagrams and call the new `generate_all_diagrams()`.

**Files:**
- Modify: `src/opencode_arch/mcp/tools/docs.py`

Add after the behaviors section:
```python
if "diagrams" in requested or "all" in requested:
    try:
        from architecture_model.docs.diagrams import generate_all_diagrams
        diag_dir = output_dir / "diagrams"
        diagram_paths = generate_all_diagrams(model, diag_dir)
        generated.extend(str(p.relative_to(path)) for p in diagram_paths)
    except Exception as e:
        errors.append(f"diagrams: {e}")
```

### Task 9: Update store_extraction() to use compaction

The `store_extraction()` in opencode-arch already does behavior noise reduction (lines 417-449). Replace that ad-hoc logic with the new `compact_for_storage()` function.

**Files:**
- Modify: `src/opencode_arch/mcp/tools/extract.py:417-449`

Replace the existing noise reduction block with:
```python
try:
    from architecture_model.orchestration.compaction import compact_for_storage
    original_count = len(model.entities.behaviors)
    model, offloaded = compact_for_storage(model)
    _save_beh(model, output_path)
    
    # Write per-component sub-models with full behaviors
    for comp_id, behaviors in offloaded.items():
        ...
    
    result["behaviors_reduced"] = f"{original_count} -> {len(model.entities.behaviors)}"
    pipeline["compaction"] = {"status": "ok"}
except Exception as e:
    pipeline["compaction"] = {"status": "error", "error": str(e)}
```

---

## Summary

| Phase | Tasks | What | Repo |
|-------|-------|------|------|
| 1 | 1-2 | Fix relationship type bugs (use-case inference, enum normalization) | arch-model-std |
| 2 | 3-4 | Create diagrams.py + wire into generate_docs() | arch-model-std |
| 3 | 5-7 | Model compaction + hierarchical output + run on logs_db | arch-model-std |
| 4 | 8-9 | Update opencode-arch tools to use new infra | opencode-arch |

**New modules:**
- `src/architecture_model/docs/diagrams.py` — Mermaid diagram generators (component, use-case, system boundary)
- `src/architecture_model/orchestration/compaction.py` — Model compaction for storage

**Key outcome:** Running `full_extraction_with_docs(repo)` produces a compact ~50KB model + full `.architecture-models/` hierarchy with docs, diagrams, sub-models, and use-case sequence diagrams.
