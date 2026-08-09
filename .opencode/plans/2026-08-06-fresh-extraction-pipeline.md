# Fresh Extraction Pipeline: Full Enrichment Suite

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build complete enrichment pipeline (behavior triggers, composite use-case behaviors, capability hierarchy, flow diagrams) then run fresh extraction on logs_db producing a rich model with level-3 decomposition and connected behavior flows.

**Architecture:** Extends existing call_graph.py and behavior_flows.py infrastructure. Adds: (1) automatic behavior-to-behavior trigger detection from call graph, (2) composite behavior inference (use cases = chains of triggered behaviors), (3) capability hierarchy from URL path depth, (4) full pipeline orchestration function that runs everything end-to-end.

**Tech Stack:** Python 3.12, pytest. Repo: `architecture-model-standard` at `/Users/baigm2/Documents/Projects/architecture-model-standard/`.

**Run tests:** `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py --ignore=tests/test_docs_gen.py`

**Key constraints:**
- 100% deterministic, zero LLM dependency
- Use existing infrastructure: `build_call_graph()`, `trace_flow()`, `classify_behaviors()`, `create_behaviors_from_manifest()`
- Use cases represented as composite Behaviors with `contains` relationships to sub-behaviors
- Capability hierarchy via `contains` relationships (parent CAP contains child CAP)
- Fresh extraction = generate everything from scratch (no incremental)

**Existing infrastructure (DO NOT rewrite):**
- `manifest/call_graph.py`: `build_call_graph(manifest)`, `trace_flow(graph, entry, max_depth=5)`, `map_flow_to_components(flow, file_to_comp)` — all working
- `orchestration/auto_enrich.py`: `create_behaviors_from_manifest(model, manifest)` — creates behaviors from router/service functions
- `orchestration/behavior_flows.py`: `classify_behaviors(behaviors, relationships, call_graph, file_to_comp)` — categorizes into trivial/CRUD/cross-component
- `orchestration/behavior_decompose.py`: `decompose_all_behaviors(model, manifest)` — raw steps → structured Steps
- `orchestration/capability_inference.py`: `infer_capabilities(model)` — flat capabilities from trigger patterns
- `core/decomposer.py`: `detect_systems(model, manifest, target_systems=0)` — system boundaries
- `manifest/grouping.py`: `group_modules(modules, interfaces)`, `create_components_from_manifest(manifest)` — component creation

---

## Phase 1: Behavior Trigger Detection

### Task 1: Implement `detect_behavior_triggers()`

**Files:**
- Create: `src/architecture_model/orchestration/trigger_detection.py`
- Test: `tests/test_trigger_detection.py`

**Concept:** Given behaviors (each with a source_file + entry function name) and a call graph, find where one behavior's execution calls the entry function of another behavior → `triggers` relationship.

Also detect endpoint chaining: if a function uses `BackgroundTasks.add_task()` or calls a function that is the entry point of another behavior.

**Step 1: Write tests**

```python
"""Tests for automatic behavior trigger detection."""
import pytest
from architecture_model.orchestration.trigger_detection import detect_behavior_triggers
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Behavior, Component, Relationship
)
from architecture_model.manifest.call_graph import CallGraph


def _make_call_graph(edges, locations=None):
    """Build a CallGraph from edge dict."""
    graph = CallGraph()
    graph.edges = edges
    graph.locations = locations or {}
    for qname in edges:
        file, fname = qname.split(":", 1)
        graph.locations[qname] = file
    # Also register targets
    for targets in edges.values():
        for t in targets:
            file, fname = t.split(":", 1)
            graph.locations.setdefault(t, file)
    return graph


class TestDetectBehaviorTriggers:
    def test_direct_call_creates_triggers_edge(self):
        """BEH-1's entry calls BEH-2's entry → triggers relationship."""
        behaviors = [
            Behavior(id="BEH-1", name="Create log", status="ACTIVE",
                     source_file="routers/logs.py", steps=["parse_text"]),
            Behavior(id="BEH-2", name="Parse text", status="ACTIVE",
                     source_file="services/parser.py", steps=["tokenize"]),
        ]
        graph = _make_call_graph({
            "routers/logs.py:create_log": ["services/parser.py:parse_text"],
            "services/parser.py:parse_text": ["services/parser.py:tokenize"],
        })
        # Map behavior to its entry function
        beh_entries = {"BEH-1": "routers/logs.py:create_log", "BEH-2": "services/parser.py:parse_text"}
        
        triggers = detect_behavior_triggers(behaviors, graph, beh_entries)
        assert len(triggers) == 1
        assert triggers[0].type == "triggers"
        assert triggers[0].from_id == "BEH-1"
        assert triggers[0].to_id == "BEH-2"

    def test_no_cross_call_no_trigger(self):
        """Independent behaviors produce no triggers."""
        behaviors = [
            Behavior(id="BEH-1", name="A", status="ACTIVE", source_file="a.py"),
            Behavior(id="BEH-2", name="B", status="ACTIVE", source_file="b.py"),
        ]
        graph = _make_call_graph({
            "a.py:func_a": ["a.py:helper_a"],
            "b.py:func_b": ["b.py:helper_b"],
        })
        beh_entries = {"BEH-1": "a.py:func_a", "BEH-2": "b.py:func_b"}
        
        triggers = detect_behavior_triggers(behaviors, graph, beh_entries)
        assert len(triggers) == 0

    def test_transitive_call_detected(self):
        """BEH-1 → helper → BEH-2's entry (indirect) → triggers."""
        behaviors = [
            Behavior(id="BEH-1", name="A", status="ACTIVE", source_file="a.py"),
            Behavior(id="BEH-2", name="B", status="ACTIVE", source_file="b.py"),
        ]
        graph = _make_call_graph({
            "a.py:func_a": ["a.py:dispatch"],
            "a.py:dispatch": ["b.py:func_b"],
            "b.py:func_b": [],
        })
        beh_entries = {"BEH-1": "a.py:func_a", "BEH-2": "b.py:func_b"}
        
        triggers = detect_behavior_triggers(behaviors, graph, beh_entries)
        assert len(triggers) == 1
        assert triggers[0].from_id == "BEH-1"
        assert triggers[0].to_id == "BEH-2"

    def test_no_self_trigger(self):
        """A behavior doesn't trigger itself."""
        behaviors = [
            Behavior(id="BEH-1", name="A", status="ACTIVE", source_file="a.py"),
        ]
        graph = _make_call_graph({
            "a.py:func_a": ["a.py:func_a"],  # recursion
        })
        beh_entries = {"BEH-1": "a.py:func_a"}
        
        triggers = detect_behavior_triggers(behaviors, graph, beh_entries)
        assert len(triggers) == 0

    def test_chain_detection(self):
        """A → B → C produces two triggers edges."""
        behaviors = [
            Behavior(id="BEH-1", name="A", status="ACTIVE", source_file="a.py"),
            Behavior(id="BEH-2", name="B", status="ACTIVE", source_file="b.py"),
            Behavior(id="BEH-3", name="C", status="ACTIVE", source_file="c.py"),
        ]
        graph = _make_call_graph({
            "a.py:func_a": ["b.py:func_b"],
            "b.py:func_b": ["c.py:func_c"],
            "c.py:func_c": [],
        })
        beh_entries = {"BEH-1": "a.py:func_a", "BEH-2": "b.py:func_b", "BEH-3": "c.py:func_c"}
        
        triggers = detect_behavior_triggers(behaviors, graph, beh_entries)
        assert len(triggers) == 2
```

**Step 2: Implement**

```python
"""Automatic behavior-to-behavior trigger detection from call graph."""
from __future__ import annotations

from architecture_model.core.types import Behavior, Relationship
from architecture_model.manifest.call_graph import CallGraph, trace_flow


def detect_behavior_triggers(
    behaviors: list[Behavior],
    call_graph: CallGraph,
    behavior_entries: dict[str, str],  # beh_id -> qname of entry function
    max_depth: int = 4,
) -> list[Relationship]:
    """Detect triggers relationships between behaviors via call graph analysis.
    
    For each behavior's entry function, trace its call graph. If the trace
    reaches the entry function of another behavior, that's a triggers edge.
    
    Also handles transitive calls (A → helper → B's entry).
    
    Args:
        behaviors: List of behaviors to analyze
        call_graph: Resolved call graph from manifest
        behavior_entries: Mapping of behavior ID to its qualified entry function name
        max_depth: Maximum call depth to trace (default 4)
    
    Returns:
        List of Relationship(type="triggers", from_id=..., to_id=...)
    """
    # Build reverse index: qname -> behavior_id (for entry functions only)
    entry_to_beh: dict[str, str] = {}
    for beh_id, qname in behavior_entries.items():
        entry_to_beh[qname] = beh_id
    
    triggers: list[Relationship] = []
    seen: set[tuple[str, str]] = set()  # deduplicate
    
    for beh in behaviors:
        entry_qname = behavior_entries.get(beh.id)
        if not entry_qname or entry_qname not in call_graph.edges:
            continue
        
        # BFS through call graph from this behavior's entry
        flow = trace_flow(call_graph, entry_qname, max_depth=max_depth)
        
        # Check if any step (except the entry itself) is another behavior's entry
        for file, fname in flow.steps:
            qname = f"{file}:{fname}"
            if qname == entry_qname:
                continue  # skip self
            if qname in entry_to_beh:
                target_beh_id = entry_to_beh[qname]
                if target_beh_id == beh.id:
                    continue  # no self-trigger
                pair = (beh.id, target_beh_id)
                if pair not in seen:
                    seen.add(pair)
                    triggers.append(Relationship(
                        type="triggers",
                        from_id=beh.id,
                        to_id=target_beh_id,
                    ))
    
    return triggers


def build_behavior_entry_map(
    behaviors: list[Behavior],
    call_graph: CallGraph,
) -> dict[str, str]:
    """Infer behavior entry function qnames from behavior name + source_file.
    
    Heuristic: behavior.name (snake_cased) matches a function in behavior.source_file.
    Falls back to first function in the source file.
    """
    entries: dict[str, str] = {}
    
    # Build file -> functions index
    file_funcs: dict[str, list[str]] = {}
    for qname, loc in call_graph.locations.items():
        file_funcs.setdefault(loc, []).append(qname)
    
    for beh in behaviors:
        if not beh.source_file:
            continue
        
        # Try exact name match
        snake_name = beh.name.lower().replace(" ", "_").replace("-", "_")
        candidate = f"{beh.source_file}:{snake_name}"
        if candidate in call_graph.edges or candidate in call_graph.locations:
            entries[beh.id] = candidate
            continue
        
        # Try matching any function in the source file
        file_qnames = file_funcs.get(beh.source_file, [])
        if file_qnames:
            # Prefer function whose name is closest to behavior name
            best = None
            best_score = -1
            for qn in file_qnames:
                fname = qn.split(":", 1)[1]
                # Simple overlap score
                score = len(set(fname) & set(snake_name))
                if score > best_score:
                    best = qn
                    best_score = score
            if best:
                entries[beh.id] = best
    
    return entries
```

---

## Phase 2: Composite Behavior Inference (Use Cases)

### Task 2: Implement `infer_composite_behaviors()`

**Files:**
- Create: `src/architecture_model/orchestration/use_case_inference.py`
- Test: `tests/test_use_case_inference.py`

**Concept:** Find chains of triggered behaviors (A triggers B triggers C) and create a composite Behavior that `contains` the chain. The composite represents the end-to-end use case.

**Step 1: Write tests**

```python
"""Tests for composite behavior (use case) inference."""
import pytest
from architecture_model.orchestration.use_case_inference import infer_composite_behaviors
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Behavior, Relationship
)


class TestInferCompositeBehaviors:
    def test_chain_becomes_composite(self):
        """A→B→C chain produces one composite behavior containing all three."""
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="Receive log", status="ACTIVE", trigger="POST /logs"),
                Behavior(id="BEH-2", name="Parse entities", status="ACTIVE", trigger="internal"),
                Behavior(id="BEH-3", name="Update graph", status="ACTIVE", trigger="internal"),
            ]),
            relationships=[
                Relationship(type="triggers", from_id="BEH-1", to_id="BEH-2"),
                Relationship(type="triggers", from_id="BEH-2", to_id="BEH-3"),
            ]
        )
        result = infer_composite_behaviors(model)
        composites = [b for b in result.entities.behaviors if b.id.startswith("UC-")]
        assert len(composites) == 1
        # Should contain all 3 behaviors
        contains_rels = [r for r in result.relationships if r.type == "contains" and r.from_id == composites[0].id]
        assert len(contains_rels) == 3

    def test_parallel_chains_separate_composites(self):
        """Two independent chains produce two composites."""
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="A", status="ACTIVE", trigger="POST /a"),
                Behavior(id="BEH-2", name="B", status="ACTIVE", trigger="internal"),
                Behavior(id="BEH-3", name="C", status="ACTIVE", trigger="POST /c"),
                Behavior(id="BEH-4", name="D", status="ACTIVE", trigger="internal"),
            ]),
            relationships=[
                Relationship(type="triggers", from_id="BEH-1", to_id="BEH-2"),
                Relationship(type="triggers", from_id="BEH-3", to_id="BEH-4"),
            ]
        )
        result = infer_composite_behaviors(model)
        composites = [b for b in result.entities.behaviors if b.id.startswith("UC-")]
        assert len(composites) == 2

    def test_single_behavior_no_composite(self):
        """Isolated behaviors without triggers don't form composites."""
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="Solo", status="ACTIVE", trigger="GET /solo"),
            ]),
            relationships=[]
        )
        result = infer_composite_behaviors(model)
        composites = [b for b in result.entities.behaviors if b.id.startswith("UC-")]
        assert len(composites) == 0

    def test_composite_inherits_trigger_from_chain_head(self):
        """Composite behavior gets the trigger of the first behavior in the chain."""
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="Create log", status="ACTIVE", trigger="POST /logs"),
                Behavior(id="BEH-2", name="Enrich", status="ACTIVE", trigger="internal"),
            ]),
            relationships=[
                Relationship(type="triggers", from_id="BEH-1", to_id="BEH-2"),
            ]
        )
        result = infer_composite_behaviors(model)
        composites = [b for b in result.entities.behaviors if b.id.startswith("UC-")]
        assert composites[0].trigger == "POST /logs"

    def test_composite_name_derived_from_chain(self):
        """Composite name combines the chain behaviors meaningfully."""
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="Submit order", status="ACTIVE", trigger="POST /orders"),
                Behavior(id="BEH-2", name="Process payment", status="ACTIVE", trigger="internal"),
                Behavior(id="BEH-3", name="Send confirmation", status="ACTIVE", trigger="internal"),
            ]),
            relationships=[
                Relationship(type="triggers", from_id="BEH-1", to_id="BEH-2"),
                Relationship(type="triggers", from_id="BEH-2", to_id="BEH-3"),
            ]
        )
        result = infer_composite_behaviors(model)
        composites = [b for b in result.entities.behaviors if b.id.startswith("UC-")]
        # Name should reference the head behavior or summarize the flow
        assert "Submit order" in composites[0].name or "order" in composites[0].name.lower()
```

**Step 2: Implement**

```python
"""Infer composite behaviors (use cases) from behavior trigger chains."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import replace as dc_replace

from architecture_model.core.types import (
    ArchitectureModel, Behavior, Entities, Relationship
)


def _find_chains(triggers: list[Relationship]) -> list[list[str]]:
    """Find linear chains in the triggers graph.
    
    A chain starts from a behavior that is NOT a target of any triggers edge
    (i.e., it's a "head" — externally triggered).
    
    Returns list of chains, each chain is ordered list of behavior IDs.
    """
    # Build adjacency
    graph: dict[str, list[str]] = defaultdict(list)
    targets: set[str] = set()
    for rel in triggers:
        graph[rel.from_id].append(rel.to_id)
        targets.add(rel.to_id)
    
    # Find heads (not targets of any trigger)
    all_sources = set(graph.keys())
    heads = all_sources - targets
    
    # Trace each chain from head
    chains = []
    visited: set[str] = set()
    for head in sorted(heads):
        chain = []
        current = head
        while current and current not in visited:
            visited.add(current)
            chain.append(current)
            nexts = graph.get(current, [])
            current = nexts[0] if nexts else None  # follow first (linear chain)
        if len(chain) >= 2:  # only interesting if 2+ behaviors
            chains.append(chain)
    
    return chains


def infer_composite_behaviors(model: ArchitectureModel) -> ArchitectureModel:
    """Create composite behaviors (use cases) from trigger chains.
    
    For each chain of ≥2 behaviors connected by triggers:
    1. Create a composite Behavior (UC-N) representing the end-to-end use case
    2. Add contains relationships from composite to each behavior in the chain
    3. Composite inherits trigger from chain head, name from head behavior
    
    Original behaviors and relationships are preserved.
    """
    triggers = [r for r in model.relationships if r.type == "triggers"]
    if not triggers:
        return model
    
    chains = _find_chains(triggers)
    if not chains:
        return model
    
    beh_index = {b.id: b for b in (model.entities.behaviors or [])}
    
    new_behaviors = []
    new_rels = []
    
    for i, chain in enumerate(chains, 1):
        head = beh_index.get(chain[0])
        if not head:
            continue
        
        # Create composite behavior
        composite = Behavior(
            id=f"UC-{i}",
            name=f"{head.name} (end-to-end)",
            status="ACTIVE",
            trigger=head.trigger,
            actor=head.actor,
            # Steps = ordered behavior names in chain
            steps=[beh_index[bid].name for bid in chain if bid in beh_index],
        )
        new_behaviors.append(composite)
        
        # Contains relationships
        for bid in chain:
            new_rels.append(Relationship(type="contains", from_id=composite.id, to_id=bid))
    
    # Merge into model
    all_behaviors = list(model.entities.behaviors or []) + new_behaviors
    all_rels = list(model.relationships) + new_rels
    
    new_entities = dc_replace(model.entities, behaviors=all_behaviors)
    return dc_replace(model, entities=new_entities, relationships=all_rels)
```

---

## Phase 3: Capability Hierarchy

### Task 3: Enhance `infer_capabilities()` with hierarchy

**Files:**
- Modify: `src/architecture_model/orchestration/capability_inference.py`
- Test: `tests/test_capability_hierarchy.py`

**Concept:** After flat capability inference, add nesting:
- `/logs` → "Log Management" (parent)
- `/logs/parse_log` → "Log Parsing" (child)
- `/logs/search` → "Log Search" (child)

Hierarchy comes from URL path depth. Capabilities sharing a prefix become children of the prefix capability.

**Step 1: Write tests**

```python
"""Tests for capability hierarchy inference."""
import pytest
from architecture_model.orchestration.capability_inference import (
    infer_capabilities, build_capability_hierarchy
)
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Behavior, Capability, Relationship
)


class TestCapabilityHierarchy:
    def test_nested_urls_create_parent_child(self):
        """Behaviors with /logs and /logs/parse get nested capabilities."""
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="Create log", status="ACTIVE", trigger="POST /logs"),
                Behavior(id="BEH-2", name="Parse log", status="ACTIVE", trigger="POST /logs/parse_log"),
                Behavior(id="BEH-3", name="Search logs", status="ACTIVE", trigger="GET /logs/search"),
                Behavior(id="BEH-4", name="Get orders", status="ACTIVE", trigger="GET /orders"),
            ]),
            relationships=[]
        )
        result = build_capability_hierarchy(infer_capabilities(model))
        contains = [r for r in result.relationships if r.type == "contains"]
        # /logs/parse and /logs/search should be children of /logs capability
        assert len(contains) >= 2

    def test_flat_urls_no_hierarchy(self):
        """All behaviors at same path depth = no contains relationships."""
        model = ArchitectureModel(
            meta=ModelMeta(project="test", schema_version="1.3"),
            entities=Entities(behaviors=[
                Behavior(id="BEH-1", name="A", status="ACTIVE", trigger="GET /users"),
                Behavior(id="BEH-2", name="B", status="ACTIVE", trigger="GET /orders"),
            ]),
            relationships=[]
        )
        result = build_capability_hierarchy(infer_capabilities(model))
        contains = [r for r in result.relationships if r.type == "contains"]
        assert len(contains) == 0
```

**Step 2: Implement `build_capability_hierarchy()`**

```python
def build_capability_hierarchy(model: ArchitectureModel) -> ArchitectureModel:
    """Add contains relationships between capabilities based on URL prefix nesting.
    
    If CAP-A covers /logs and CAP-B covers /logs/parse, 
    then CAP-A contains CAP-B.
    """
    caps = model.entities.capabilities or []
    if len(caps) < 2:
        return model
    
    # Extract URL prefix for each capability from its realized behaviors
    cap_prefixes: dict[str, str] = {}  # cap_id -> url prefix
    realizes = [r for r in model.relationships if r.type == "realizes"]
    beh_index = {b.id: b for b in (model.entities.behaviors or [])}
    
    for cap in caps:
        # Find behaviors that realize this capability
        beh_ids = [r.from_id for r in realizes if r.to_id == cap.id]
        # Extract common URL prefix from behaviors
        prefixes = []
        for bid in beh_ids:
            beh = beh_index.get(bid)
            if beh and beh.trigger:
                match = re.search(r'/([\w/-]+)', beh.trigger)
                if match:
                    prefixes.append(match.group(1).split("/")[0])
        if prefixes:
            cap_prefixes[cap.id] = prefixes[0]  # use first segment
    
    # Find parent-child relationships based on prefix containment
    new_rels = list(model.relationships)
    for child_cap in caps:
        child_prefix = cap_prefixes.get(child_cap.id, "")
        if "/" not in child_prefix:
            continue  # can't be a child
        parent_prefix = child_prefix.rsplit("/", 1)[0]
        for parent_cap in caps:
            if parent_cap.id == child_cap.id:
                continue
            if cap_prefixes.get(parent_cap.id) == parent_prefix:
                new_rels.append(Relationship(type="contains", from_id=parent_cap.id, to_id=child_cap.id))
    
    return dc_replace(model, relationships=new_rels)
```

Note: This implementation may need refinement — the prefix matching needs to look at FULL URL paths from behaviors, not just first segments. Adjust based on test results.

---

## Phase 4: Full Extraction Pipeline

### Task 4: Create `full_extraction()` orchestration function

**Files:**
- Create: `src/architecture_model/orchestration/full_extraction.py`
- Test: `tests/test_full_extraction.py`

**Concept:** One function that runs the entire pipeline end-to-end:

```python
def full_extraction(repo_path: Path) -> ArchitectureModel:
    """Run complete architecture extraction pipeline.
    
    Pipeline:
    1. Generate manifest (AST scan)
    2. Build call graph
    3. Group modules into components
    4. Create initial model
    5. Detect system boundaries
    6. Create behaviors from manifest
    7. Detect behavior triggers (call graph + endpoint chaining)
    8. Classify behaviors (trivial/CRUD/cross-component)
    9. Decompose behaviors (raw steps → structured Steps)
    10. Infer composite behaviors (use cases from trigger chains)
    11. Infer capabilities (from trigger patterns)
    12. Build capability hierarchy
    13. Validate model
    14. Return enriched model
    """
```

**Tests:**

```python
def test_full_extraction_on_tmp_project(tmp_path):
    """Full pipeline produces valid model with all entity types."""
    # Create minimal project
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("")
    (tmp_path / "app" / "models.py").write_text("class User: pass\nclass Order: pass\n")
    (tmp_path / "app" / "routes.py").write_text('''
def get_user():
    return query_user()

def create_order():
    return process_order()
''')
    (tmp_path / "app" / "services.py").write_text('''
from app.models import User, Order

def query_user():
    return User()

def process_order():
    order = Order()
    notify_user()
    return order

def notify_user():
    pass
''')
    
    from architecture_model.orchestration.full_extraction import full_extraction
    model = full_extraction(tmp_path)
    
    assert len(model.entities.components) >= 1
    assert len(model.entities.behaviors) >= 1
    # Should have some relationships
    assert len(model.relationships) >= 1


def test_full_extraction_produces_systems(tmp_path):
    """Pipeline detects system boundaries."""
    # Create multi-directory project
    for subdir in ["billing", "notifications"]:
        (tmp_path / subdir).mkdir()
        (tmp_path / subdir / "__init__.py").write_text("")
        (tmp_path / subdir / "main.py").write_text(f"def run_{subdir}(): pass\n")
    
    from architecture_model.orchestration.full_extraction import full_extraction
    model = full_extraction(tmp_path)
    
    assert len(model.entities.systems) >= 1
```

---

## Phase 5: Run Fresh Extraction on logs_db

### Task 5: Execute full_extraction on logs_db

**Not a code task** — this is running the pipeline and evaluating results.

```bash
/opt/anaconda3/bin/python -c "
from pathlib import Path
from architecture_model.orchestration.full_extraction import full_extraction
from architecture_model.core.parser import save_model
from architecture_model.core.validator import validate_model

repo = Path('/Users/baigm2/Documents/Projects/logs_db')
model = full_extraction(repo)

# Print summary
print(f'Components: {len(model.entities.components)}')
print(f'Systems: {len(model.entities.systems)}')
print(f'Behaviors: {len(model.entities.behaviors)}')
print(f'Capabilities: {len(model.entities.capabilities)}')
print(f'Relationships: {len(model.relationships)}')

# Break down relationships by type
from collections import Counter
rel_types = Counter(r.type for r in model.relationships)
for rtype, count in rel_types.most_common():
    print(f'  {rtype}: {count}')

# Show use cases
composites = [b for b in model.entities.behaviors if b.id.startswith('UC-')]
print(f'\nUse Cases (composites): {len(composites)}')
for uc in composites:
    print(f'  {uc.id}: {uc.name}')
    print(f'    Trigger: {uc.trigger}')
    print(f'    Steps: {uc.steps}')

# Show capabilities
print(f'\nCapabilities:')
for cap in model.entities.capabilities:
    print(f'  {cap.id}: {cap.name}')

# Show systems
print(f'\nSystems:')
for sys in model.entities.systems:
    print(f'  {sys.id}: {sys.name} ({len(sys.component_ids)} components)')

# Validate
result = validate_model(model)
print(f'\nValidation score: {result.score}')

# Save
save_model(model, repo / '.architecture-model-v2.yaml')
print(f'\nSaved to .architecture-model-v2.yaml')
"
```

### Task 6: Evaluate and iterate

Review the extraction results:
- Are use cases meaningful? Do they represent real end-to-end workflows?
- Are capabilities well-named and properly hierarchical?
- Are systems correctly identified?
- Are behavior flows connected (trigger chains visible)?
- Is the level-3 decomposition visible in structured_steps?

If needed, tune parameters:
- `target_systems` for system detection
- `max_depth` for trigger chain detection
- Capability naming heuristics
- Composite behavior naming

### Task 7: Save final model and commit

Once satisfied, save as the new `.architecture-model.yaml` for logs_db.

---

## Summary

| Phase | Tasks | New Code | Purpose |
|-------|-------|----------|---------|
| 1 | 1 | `trigger_detection.py` | Auto-detect behavior→behavior flows from call graph |
| 2 | 2 | `use_case_inference.py` | Group trigger chains into composite use-case behaviors |
| 3 | 3 | Enhance `capability_inference.py` | Add capability hierarchy from URL nesting |
| 4 | 4 | `full_extraction.py` | Single function runs entire pipeline end-to-end |
| 5 | 5-7 | (scripts/config) | Run on logs_db, evaluate, save |

**New functions:**
- `detect_behavior_triggers(behaviors, call_graph, behavior_entries)` → `list[Relationship]`
- `build_behavior_entry_map(behaviors, call_graph)` → `dict[str, str]`
- `infer_composite_behaviors(model)` → `ArchitectureModel`
- `build_capability_hierarchy(model)` → `ArchitectureModel`
- `full_extraction(repo_path)` → `ArchitectureModel`

**Expected logs_db output:**
- ~9 components (same as current)
- 3-5 systems (from `detect_systems`)
- ~28 leaf behaviors + N composite use-case behaviors
- ~12 capabilities with hierarchy
- `triggers` relationships connecting behavior flows
- `contains` relationships for use-case → behavior and capability → sub-capability
- Structured steps on all behaviors with component refs
