# System-of-Systems Detection + Capability Generation + Behavior Decomposition

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build general-purpose tooling in `architecture-model-standard` for (1) multi-signal system boundary detection, (2) capability inference from behaviors, and (3) structured behavior sub-decomposition. Then apply to logs_db.

**Architecture:** Extends the existing `decomposer.py` system detection with multi-signal affinity (imports, data, API surface, directory). Adds capability inference that clusters behaviors into user-facing capabilities. Promotes `Behavior.steps` from `list[str]` to `list[Step]` with structured sub-behaviors.

**Tech Stack:** Python 3.12, pytest. Repo: `architecture-model-standard` at `/Users/baigm2/Documents/Projects/architecture-model-standard/`.

**Run tests:** `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py --ignore=tests/test_docs_gen.py`

**Key constraints:**
- 100% deterministic, zero LLM dependency
- Systems CONTAIN Components (container layer via `component_ids`)
- Aggressive decomposition (many small systems, 2-5+ per repo)
- Report all candidates with independence scores; let user/agent decide cutoff
- Backward compatible: existing models with `steps: list[str]` still parse

---

## Phase 1: Multi-Signal System Detector

Replace the current complexity-only `identify_systems()` with a multi-signal boundary detector.

### Task 1: Define SystemScore dataclass and new function signature

**Files:**
- Modify: `src/architecture_model/core/decomposer.py`
- Test: `tests/test_system_detector.py`

**Step 1: Write failing tests**

```python
# tests/test_system_detector.py
"""Tests for multi-signal system boundary detection."""
import pytest
from architecture_model.core.decomposer import detect_systems, SystemScore
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Component, Relationship, System
)
from architecture_model.manifest.generator import Manifest, ModuleInfo, FunctionInfo


def _make_manifest(modules):
    """Helper to build a Manifest from module specs."""
    from architecture_model.manifest.generator import Manifest, MetricsResult
    from datetime import datetime
    module_infos = []
    for m in modules:
        module_infos.append(ModuleInfo(
            file=m["file"], name=m.get("name", m["file"]),
            docstring="", functions=[FunctionInfo(name=f, signature=f"def {f}()") for f in m.get("functions", [])],
            imports=m.get("imports", []), line_count=m.get("lines", 50),
            status="active", classes=[]
        ))
    return Manifest(
        modules=module_infos, interfaces=[],
        functional_blocks={}, generated_at=datetime.now().isoformat(),
        project_root="/tmp/test", metrics=MetricsResult(values={})
    )


def _make_model(components):
    """Helper to build a model from component specs."""
    comps = []
    for c in components:
        comps.append(Component(
            id=c["id"], name=c["name"], status="ACTIVE",
            source_files=c.get("files", [])
        ))
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(components=comps),
        relationships=[Relationship(type=r["type"], from_id=r["from"], to_id=r["to"]) for r in components[0].get("rels", [])] if components else []
    )


class TestDetectSystems:
    def test_returns_system_scores(self):
        """detect_systems returns SystemScore objects with independence scores."""
        manifest = _make_manifest([
            {"file": "api/users.py", "imports": ["models.user"], "functions": ["get_user", "create_user"]},
            {"file": "api/posts.py", "imports": ["models.post"], "functions": ["get_posts"]},
            {"file": "models/user.py", "imports": [], "functions": ["User"]},
            {"file": "models/post.py", "imports": [], "functions": ["Post"]},
            {"file": "services/auth.py", "imports": ["models.user"], "functions": ["login", "logout"]},
            {"file": "services/feed.py", "imports": ["models.post", "models.user"], "functions": ["build_feed"]},
        ])
        model = _make_model([
            {"id": "COMP-1", "name": "Users API", "files": ["api/users.py", "models/user.py", "services/auth.py"]},
            {"id": "COMP-2", "name": "Posts API", "files": ["api/posts.py", "models/post.py", "services/feed.py"]},
        ])
        results = detect_systems(model, manifest)
        assert len(results) >= 1
        assert all(isinstance(r, SystemScore) for r in results)
        assert all(0 <= r.independence <= 1.0 for r in results)

    def test_independent_modules_form_separate_systems(self):
        """Modules with no cross-imports should be in separate systems."""
        manifest = _make_manifest([
            {"file": "billing/charge.py", "imports": ["billing.models"], "functions": ["charge"]},
            {"file": "billing/models.py", "imports": [], "functions": ["Invoice"]},
            {"file": "notifications/email.py", "imports": ["notifications.templates"], "functions": ["send"]},
            {"file": "notifications/templates.py", "imports": [], "functions": ["render"]},
        ])
        model = _make_model([
            {"id": "COMP-1", "name": "Billing", "files": ["billing/charge.py", "billing/models.py"]},
            {"id": "COMP-2", "name": "Notifications", "files": ["notifications/email.py", "notifications/templates.py"]},
        ])
        results = detect_systems(model, manifest)
        assert len(results) >= 2
        # Both should have high independence (no cross-boundary imports)
        for r in results:
            assert r.independence > 0.7

    def test_tightly_coupled_modules_form_one_system(self):
        """Modules with heavy cross-imports should cluster into one system."""
        manifest = _make_manifest([
            {"file": "core/engine.py", "imports": ["core.config", "core.state"], "functions": ["run"]},
            {"file": "core/config.py", "imports": ["core.state"], "functions": ["load"]},
            {"file": "core/state.py", "imports": ["core.engine"], "functions": ["save"]},
        ])
        model = _make_model([
            {"id": "COMP-1", "name": "Engine", "files": ["core/engine.py"]},
            {"id": "COMP-2", "name": "Config", "files": ["core/config.py"]},
            {"id": "COMP-3", "name": "State", "files": ["core/state.py"]},
        ])
        results = detect_systems(model, manifest)
        # Should form one system (too coupled to split)
        big_systems = [r for r in results if len(r.component_ids) > 1]
        assert len(big_systems) >= 1
        assert set(big_systems[0].component_ids) == {"COMP-1", "COMP-2", "COMP-3"}

    def test_data_affinity_groups_modules(self):
        """Modules importing the same models belong together."""
        manifest = _make_manifest([
            {"file": "api/orders.py", "imports": ["models.order", "models.line_item"], "functions": ["create_order"]},
            {"file": "services/shipping.py", "imports": ["models.order", "models.address"], "functions": ["ship"]},
            {"file": "models/order.py", "imports": [], "functions": ["Order"]},
            {"file": "models/line_item.py", "imports": ["models.order"], "functions": ["LineItem"]},
            {"file": "models/address.py", "imports": [], "functions": ["Address"]},
            {"file": "analytics/reports.py", "imports": ["models.order"], "functions": ["revenue"]},
        ])
        model = _make_model([
            {"id": "COMP-1", "name": "Orders", "files": ["api/orders.py", "models/order.py", "models/line_item.py"]},
            {"id": "COMP-2", "name": "Shipping", "files": ["services/shipping.py", "models/address.py"]},
            {"id": "COMP-3", "name": "Analytics", "files": ["analytics/reports.py"]},
        ])
        results = detect_systems(model, manifest)
        # Orders and Shipping share data (models.order) — may cluster or score lower independence
        assert len(results) >= 1
```

**Step 2: Define SystemScore dataclass**

```python
@dataclass
class SystemScore:
    """A proposed system boundary with multi-signal independence score."""
    name: str
    component_ids: list[str]
    independence: float  # 0-1, how extractable this system is
    signals: dict[str, float]  # individual signal scores
    # signals keys: "import_cohesion", "data_affinity", "api_surface", "directory_cohesion"
```

**Step 3: Implement `detect_systems()`**

```python
def detect_systems(
    model: ArchitectureModel,
    manifest: Manifest,
    min_components: int = 1,
) -> list[SystemScore]:
    """Detect system boundaries using multi-signal analysis.
    
    Signals:
    1. Import cohesion: ratio of internal vs external imports per component cluster
    2. Data affinity: shared model/schema imports indicate same bounded context
    3. API surface: components with HTTP endpoints form boundary layers
    4. Directory cohesion: co-located files suggest same system
    
    Strategy:
    - Start with components as atomic units
    - Compute pairwise affinity between components using all 4 signals
    - Agglomerative clustering: merge pairs with highest affinity until target reached
    - Score each resulting cluster's independence (inverse of external coupling)
    """
```

---

### Task 2: Implement import cohesion signal

**Files:**
- Modify: `src/architecture_model/core/decomposer.py`

**Step 1: Write helper function**

```python
def _import_cohesion(comp_files: set[str], all_imports: dict[str, list[str]]) -> float:
    """Ratio of imports that stay within comp_files vs go outside.
    
    Returns 1.0 if all imports are internal, 0.0 if all are external.
    """
    internal = 0
    external = 0
    for f in comp_files:
        for imp in all_imports.get(f, []):
            # Check if the import target resolves to a file in comp_files
            if _import_resolves_to(imp, comp_files):
                internal += 1
            else:
                external += 1
    total = internal + external
    return internal / total if total > 0 else 1.0
```

**Step 2: Write helper for import resolution**

```python
def _import_resolves_to(imp: str, file_set: set[str]) -> bool:
    """Check if an import string (e.g., 'models.user') resolves to a file in file_set."""
    # Convert import path to possible file paths
    parts = imp.split(".")
    candidates = [
        "/".join(parts) + ".py",
        "/".join(parts) + "/__init__.py",
        "/".join(parts[:-1]) + ".py" if len(parts) > 1 else "",
    ]
    return any(c in file_set or any(f.endswith(c) for f in file_set) for c in candidates if c)
```

---

### Task 3: Implement data affinity signal

**Files:**
- Modify: `src/architecture_model/core/decomposer.py`

```python
def _data_affinity(comp1_files: set[str], comp2_files: set[str], 
                   all_imports: dict[str, list[str]], model_files: set[str]) -> float:
    """Score based on shared data model imports between two component clusters.
    
    model_files: files identified as data models (e.g., in models/ dir or defining ORM classes)
    
    Returns 0-1: 1.0 if both clusters import the exact same set of models.
    """
    models1 = set()
    models2 = set()
    for f in comp1_files:
        for imp in all_imports.get(f, []):
            if _import_resolves_to(imp, model_files):
                models1.add(imp)
    for f in comp2_files:
        for imp in all_imports.get(f, []):
            if _import_resolves_to(imp, model_files):
                models2.add(imp)
    if not models1 and not models2:
        return 0.0
    intersection = models1 & models2
    union = models1 | models2
    return len(intersection) / len(union) if union else 0.0
```

---

### Task 4: Implement directory cohesion and API surface signals

**Files:**
- Modify: `src/architecture_model/core/decomposer.py`

```python
def _directory_cohesion(files: set[str]) -> float:
    """How concentrated are files in the same directory tree?
    
    Returns 1.0 if all files share a common non-root prefix.
    Returns lower values if spread across many top-level dirs.
    """
    if not files:
        return 0.0
    dirs = set()
    for f in files:
        parts = f.split("/")
        if len(parts) > 1:
            dirs.add(parts[0])
        else:
            dirs.add(".")
    return 1.0 / len(dirs) if dirs else 0.0


def _has_api_surface(files: set[str], manifest_modules: list) -> bool:
    """Check if any file in this set exposes HTTP endpoints."""
    api_indicators = {"router", "route", "endpoint", "view", "api", "handler"}
    for f in files:
        parts = f.lower().replace("/", ".").replace(".py", "").split(".")
        if any(indicator in parts for indicator in api_indicators):
            return True
    # Also check function names for HTTP-verb patterns
    for mod in manifest_modules:
        if mod.file in files:
            for func in mod.functions:
                if func.name.lower() in ("get", "post", "put", "delete", "patch"):
                    return True
    return False
```

---

### Task 5: Implement pairwise affinity + agglomerative clustering

**Files:**
- Modify: `src/architecture_model/core/decomposer.py`

This is the core algorithm. Compute pairwise affinity between components, then agglomeratively cluster them.

```python
def _compute_pairwise_affinity(
    components: list[Component],
    manifest_imports: dict[str, list[str]],
    model_files: set[str],
) -> dict[tuple[str, str], float]:
    """Compute affinity score between each pair of components.
    
    Affinity = weighted combination of:
    - Import coupling (0.4): what fraction of comp1's imports go to comp2?
    - Data affinity (0.3): do they share model imports?
    - Directory cohesion (0.2): are they co-located?
    - API boundary (0.1): penalty if both have API surface (suggests separate services)
    """
    ...


def _agglomerative_cluster(
    components: list[Component],
    affinities: dict[tuple[str, str], float],
    target_systems: int = 0,
) -> list[list[str]]:
    """Merge component pairs by highest affinity until target reached.
    
    target_systems=0: auto-calculate as sqrt(len(components)) * 1.5
    (aggressive = more systems)
    """
    ...
```

**Target calculation for aggressive decomposition:**
```python
if target_systems == 0:
    # Aggressive: aim for many small systems
    target_systems = max(2, int(len(components) ** 0.6))
```

---

### Task 6: Assemble detect_systems() and compute independence scores

**Files:**
- Modify: `src/architecture_model/core/decomposer.py`

```python
def detect_systems(
    model: ArchitectureModel,
    manifest,  # Manifest type
    target_systems: int = 0,
    min_components: int = 1,
) -> list[SystemScore]:
    """Detect system boundaries using multi-signal analysis."""
    components = model.entities.components if hasattr(model.entities, 'components') else []
    if not components:
        return []
    
    # Build import index from manifest
    manifest_imports = {}
    for mod in manifest.modules:
        manifest_imports[mod.file] = mod.imports
    
    # Identify model/data files (heuristic: in models/ dir or named *model*)
    all_files = {mod.file for mod in manifest.modules}
    model_files = {f for f in all_files if "model" in f.lower() or "/models/" in f}
    
    # Compute pairwise affinity
    affinities = _compute_pairwise_affinity(components, manifest_imports, model_files)
    
    # Cluster
    clusters = _agglomerative_cluster(components, affinities, target_systems)
    
    # Score each cluster's independence
    results = []
    for cluster_comp_ids in clusters:
        cluster_files = set()
        for comp in components:
            if comp.id in cluster_comp_ids:
                cluster_files.update(comp.source_files)
        
        # Independence = internal cohesion - external coupling
        cohesion = _import_cohesion(cluster_files, manifest_imports)
        dir_score = _directory_cohesion(cluster_files)
        
        # External coupling: what fraction of other components import us?
        external_files = all_files - cluster_files
        external_imports_to_us = 0
        total_external_imports = 0
        for f in external_files:
            for imp in manifest_imports.get(f, []):
                total_external_imports += 1
                if _import_resolves_to(imp, cluster_files):
                    external_imports_to_us += 1
        
        coupling = external_imports_to_us / total_external_imports if total_external_imports > 0 else 0
        independence = (cohesion * 0.5 + dir_score * 0.3 + (1 - coupling) * 0.2)
        
        # Name from largest component or directory
        name = _infer_system_name(cluster_comp_ids, components)
        
        results.append(SystemScore(
            name=name,
            component_ids=cluster_comp_ids,
            independence=round(independence, 3),
            signals={
                "import_cohesion": round(cohesion, 3),
                "directory_cohesion": round(dir_score, 3),
                "external_coupling": round(coupling, 3),
            }
        ))
    
    return sorted(results, key=lambda s: s.independence, reverse=True)
```

**Step: Run tests, fix until passing. Commit.**

---

### Task 7: Wire detect_systems into pipeline + add MCP tool

**Files:**
- Modify: `src/architecture_model/orchestration/pipeline.py` (optional — add `system_detection` step)
- Modify: `/Users/baigm2/Documents/Projects/opencode-arch/src/opencode_arch/mcp/tools/scan.py` (include systems in scan output)

Add systems to scan output so the agent sees them. The existing `architect_scan` tool returns manifest data — augment it to include detected systems when a model exists.

---

## Phase 2: Capability Inference

### Task 8: Design capability inference from behaviors

**Files:**
- Create: `src/architecture_model/orchestration/capability_inference.py`
- Test: `tests/test_capability_inference.py`

**Concept:** Group behaviors by trigger pattern (HTTP endpoint prefix, actor, domain area) into Capabilities. Each Capability represents "what value does this deliver?"

**Step 1: Write tests**

```python
# tests/test_capability_inference.py
from architecture_model.orchestration.capability_inference import infer_capabilities
from architecture_model.core.types import (
    ArchitectureModel, ModelMeta, Entities, Behavior, Capability, Relationship
)


def test_groups_behaviors_by_endpoint_prefix():
    """Behaviors with same URL prefix cluster into one capability."""
    model = ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(behaviors=[
            Behavior(id="BEH-1", name="Create user", status="ACTIVE", trigger="POST /users"),
            Behavior(id="BEH-2", name="Get user", status="ACTIVE", trigger="GET /users/{id}"),
            Behavior(id="BEH-3", name="List orders", status="ACTIVE", trigger="GET /orders"),
            Behavior(id="BEH-4", name="Create order", status="ACTIVE", trigger="POST /orders"),
        ]),
        relationships=[]
    )
    result = infer_capabilities(model)
    assert len(result.entities.capabilities) >= 2
    # Should have "User Management" and "Order Management" or similar
    cap_names = {c.name.lower() for c in result.entities.capabilities}
    assert any("user" in n for n in cap_names)
    assert any("order" in n for n in cap_names)


def test_groups_by_actor():
    """Behaviors with same actor cluster together."""
    model = ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(behaviors=[
            Behavior(id="BEH-1", name="Login", status="ACTIVE", actor="end_user", trigger="POST /auth/login"),
            Behavior(id="BEH-2", name="Signup", status="ACTIVE", actor="end_user", trigger="POST /auth/signup"),
            Behavior(id="BEH-3", name="Run migration", status="ACTIVE", actor="admin", trigger="POST /admin/migrate"),
        ]),
        relationships=[]
    )
    result = infer_capabilities(model)
    assert len(result.entities.capabilities) >= 2


def test_creates_realizes_relationships():
    """Each behavior gets a realizes relationship to its capability."""
    model = ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(behaviors=[
            Behavior(id="BEH-1", name="Create user", status="ACTIVE", trigger="POST /users"),
            Behavior(id="BEH-2", name="Get user", status="ACTIVE", trigger="GET /users/{id}"),
        ]),
        relationships=[]
    )
    result = infer_capabilities(model)
    realizes = [r for r in result.relationships if r.type == "realizes"]
    assert len(realizes) == 2


def test_preserves_existing_capabilities():
    """If model already has capabilities, don't overwrite."""
    model = ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(
            capabilities=[Capability(id="CAP-1", name="Existing", status="ACTIVE")],
            behaviors=[
                Behavior(id="BEH-1", name="Do thing", status="ACTIVE", trigger="POST /things"),
            ]
        ),
        relationships=[]
    )
    result = infer_capabilities(model)
    assert any(c.name == "Existing" for c in result.entities.capabilities)
```

**Step 2: Implement**

```python
def infer_capabilities(model: ArchitectureModel) -> ArchitectureModel:
    """Infer user-facing capabilities from behavior patterns.
    
    Clustering strategy (in priority order):
    1. URL prefix: /users/*, /orders/* → "User Management", "Order Management"
    2. Actor: same actor → same capability
    3. Source file: behaviors from same source → same capability
    
    Naming: capitalize the URL prefix segment or actor name.
    """
```

---

### Task 9: Implement capability inference logic

**Files:**
- Modify: `src/architecture_model/orchestration/capability_inference.py`

```python
import re
from collections import defaultdict
from architecture_model.core.types import (
    ArchitectureModel, Capability, Relationship, Entities
)


def _extract_url_prefix(trigger: str) -> str | None:
    """Extract the first path segment from a trigger like 'POST /users/{id}'."""
    match = re.search(r'/([\w-]+)', trigger)
    return match.group(1) if match else None


def _name_from_prefix(prefix: str) -> str:
    """Convert URL prefix to capability name: 'users' → 'User Management'."""
    singular = prefix.rstrip("s") if prefix.endswith("s") and len(prefix) > 3 else prefix
    return f"{singular.replace('_', ' ').replace('-', ' ').title()} Management"


def infer_capabilities(model: ArchitectureModel) -> ArchitectureModel:
    """Infer capabilities from behaviors, add to model."""
    behaviors = model.entities.behaviors or []
    if not behaviors:
        return model
    
    # Preserve existing capabilities
    existing_caps = list(model.entities.capabilities or [])
    existing_rels = list(model.relationships)
    
    # Group behaviors by URL prefix first, then by actor
    prefix_groups = defaultdict(list)
    ungrouped = []
    
    for beh in behaviors:
        prefix = _extract_url_prefix(beh.trigger) if beh.trigger else None
        if prefix:
            prefix_groups[prefix].append(beh)
        elif beh.actor:
            prefix_groups[f"actor:{beh.actor}"].append(beh)
        else:
            ungrouped.append(beh)
    
    # Create capabilities for each group
    new_caps = []
    new_rels = []
    cap_counter = len(existing_caps) + 1
    
    for key, behs in prefix_groups.items():
        cap_id = f"CAP-{cap_counter}"
        if key.startswith("actor:"):
            name = f"{key[6:].replace('_', ' ').title()} Operations"
        else:
            name = _name_from_prefix(key)
        
        cap = Capability(id=cap_id, name=name, status="ACTIVE")
        new_caps.append(cap)
        
        for beh in behs:
            new_rels.append(Relationship(type="realizes", from_id=beh.id, to_id=cap_id))
        
        cap_counter += 1
    
    # Ungrouped behaviors get a "Miscellaneous" capability if any exist
    if ungrouped:
        cap_id = f"CAP-{cap_counter}"
        cap = Capability(id=cap_id, name="Internal Operations", status="ACTIVE")
        new_caps.append(cap)
        for beh in ungrouped:
            new_rels.append(Relationship(type="realizes", from_id=beh.id, to_id=cap_id))
    
    # Build new model with merged entities
    new_entities = Entities(
        components=model.entities.components,
        capabilities=existing_caps + new_caps,
        behaviors=behaviors,
        constraints=model.entities.constraints,
        interfaces=model.entities.interfaces,
        layers=model.entities.layers,
        actors=model.entities.actors,
        systems=model.entities.systems,
        decisions=model.entities.decisions,
    )
    
    return ArchitectureModel(
        meta=model.meta,
        entities=new_entities,
        relationships=existing_rels + new_rels,
    )
```

**Step: Run tests, commit.**

---

## Phase 3: Structured Behavior Decomposition

### Task 10: Add Step dataclass

**Files:**
- Modify: `src/architecture_model/core/types.py`
- Test: `tests/test_step_dataclass.py`

**Step 1: Write test**

```python
def test_step_dataclass():
    from architecture_model.core.types import Step
    step = Step(
        order=1,
        action="Validate input parameters",
        component_ref="COMP-1",
        actor="system",
    )
    assert step.order == 1
    assert step.action == "Validate input parameters"
    assert step.component_ref == "COMP-1"
```

**Step 2: Add dataclass**

```python
@dataclass
class Step:
    """A structured step within a behavior sequence."""
    order: int = 0
    action: str = ""  # Human-readable description of what happens
    component_ref: str = ""  # Component that performs this step
    actor: str = ""  # Who/what initiates (system, user, external)
    input: str = ""  # What goes in
    output: str = ""  # What comes out
    error_handling: str = ""  # What happens on failure
```

---

### Task 11: Update Behavior to support structured steps

**Files:**
- Modify: `src/architecture_model/core/types.py`
- Modify: `src/architecture_model/core/parser.py` (serialize/deserialize)
- Test: `tests/test_behavior_steps.py`

**Backward compatibility:** `Behavior.steps` stays as `list[str]`. Add new field `structured_steps: list[Step]`. The parser should:
- On input: if steps items are dicts, parse as Step objects into `structured_steps`; if strings, keep in `steps`
- On output: serialize `structured_steps` if present, otherwise `steps`

```python
# In Behavior dataclass, add:
structured_steps: list[Step] = field(default_factory=list)
```

**Test:**
```python
def test_behavior_with_structured_steps():
    from architecture_model.core.types import Behavior, Step
    beh = Behavior(
        id="BEH-1", name="Create user", status="ACTIVE",
        structured_steps=[
            Step(order=1, action="Validate email format", component_ref="COMP-1"),
            Step(order=2, action="Check for existing user", component_ref="COMP-2"),
            Step(order=3, action="Create user record", component_ref="COMP-2"),
        ]
    )
    assert len(beh.structured_steps) == 3
    assert beh.structured_steps[0].action == "Validate email format"

def test_parser_roundtrip_structured_steps(tmp_path):
    """Model with structured steps serializes and deserializes correctly."""
    from architecture_model.core.types import ArchitectureModel, ModelMeta, Entities, Behavior, Step
    from architecture_model.core.parser import save_model, load_model
    
    model = ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(behaviors=[
            Behavior(id="BEH-1", name="Test", status="ACTIVE",
                     structured_steps=[Step(order=1, action="Do thing", component_ref="COMP-1")])
        ]),
        relationships=[]
    )
    path = tmp_path / "model.yaml"
    save_model(model, path)
    loaded = load_model(path)
    assert len(loaded.entities.behaviors[0].structured_steps) == 1
    assert loaded.entities.behaviors[0].structured_steps[0].action == "Do thing"
```

---

### Task 12: Implement behavior decomposition function

**Files:**
- Create: `src/architecture_model/orchestration/behavior_decompose.py`
- Test: `tests/test_behavior_decompose.py`

**Concept:** Given a behavior with raw AST steps and a manifest, promote to structured Steps by:
1. Mapping each raw step (function call name) to its source component
2. Inferring action descriptions from function signatures/docstrings
3. Ordering by call sequence

```python
def decompose_behavior(
    behavior: Behavior,
    model: ArchitectureModel,
    manifest,  # Manifest
) -> Behavior:
    """Promote behavior's raw steps to structured Steps.
    
    For each raw step (a function/method name):
    1. Find which module/component contains this function
    2. Get its signature/docstring for action description
    3. Build a Step with component_ref and action
    
    Returns updated behavior with structured_steps populated.
    """
```

**Test:**
```python
def test_decompose_maps_steps_to_components():
    """Raw function call steps get mapped to their owning components."""
    from architecture_model.orchestration.behavior_decompose import decompose_behavior
    from architecture_model.core.types import Behavior, ArchitectureModel, ModelMeta, Entities, Component
    # ... setup with manifest containing function definitions
    
    beh = Behavior(
        id="BEH-1", name="Create log", status="ACTIVE",
        steps=["validate_input", "create_record", "emit_event"],
        source_file="app/routers/logs.py"
    )
    # manifest has modules where these functions live
    result = decompose_behavior(beh, model, manifest)
    assert len(result.structured_steps) == 3
    assert result.structured_steps[0].component_ref != ""
```

---

## Phase 4: Apply to logs_db

### Task 13: Run system detection on logs_db

```bash
/opt/anaconda3/bin/python -c "
from pathlib import Path
from architecture_model.manifest.generator import generate_manifest
from architecture_model.core.parser import load_model
from architecture_model.core.decomposer import detect_systems

repo = Path('/Users/baigm2/Documents/Projects/logs_db')
manifest = generate_manifest(repo)
model = load_model(repo / '.architecture-model.yaml')
systems = detect_systems(model, manifest)
for s in systems:
    print(f'{s.name}: {len(s.component_ids)} components, independence={s.independence}')
    print(f'  Components: {s.component_ids}')
    print(f'  Signals: {s.signals}')
    print()
"
```

Evaluate results. Expected: 3-5 systems (Search/Embedding, Document Intelligence, LLM Pipeline, Graph/Architecture, Core CRUD).

### Task 14: Run capability inference on logs_db

```bash
/opt/anaconda3/bin/python -c "
from pathlib import Path
from architecture_model.core.parser import load_model, save_model
from architecture_model.orchestration.capability_inference import infer_capabilities

repo = Path('/Users/baigm2/Documents/Projects/logs_db')
model = load_model(repo / '.architecture-model.yaml')
enriched = infer_capabilities(model)
print(f'Capabilities inferred: {len(enriched.entities.capabilities)}')
for cap in enriched.entities.capabilities:
    print(f'  {cap.id}: {cap.name}')
# Don't save yet — evaluate first
"
```

### Task 15: Run behavior decomposition on logs_db

Apply `decompose_behavior()` to all 28 root behaviors. Evaluate how well the function-name-to-component mapping works.

### Task 16: Save enriched model and validate

After reviewing results from Tasks 13-15, save the enriched model with systems, capabilities, and structured_steps. Run validation. Commit.

---

## Summary

| Phase | Tasks | What | New Code |
|-------|-------|------|----------|
| 1 | 1-7 | Multi-signal system detector | `decomposer.py` rewrite |
| 2 | 8-9 | Capability inference | `capability_inference.py` |
| 3 | 10-12 | Step dataclass + behavior decomposition | `types.py`, `behavior_decompose.py` |
| 4 | 13-16 | Apply to logs_db | Script/manual |

**New dataclasses:** `SystemScore`, `Step`
**New functions:** `detect_systems()`, `infer_capabilities()`, `decompose_behavior()`
**Modified:** `decomposer.py` (replace complexity-only with multi-signal), `types.py` (Step + Behavior.structured_steps), `parser.py` (Step serialization)
