# Representativeness Metric Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a representativeness metric that mechanically verifies an architecture model is 100% representative of the actual codebase, using three sub-scores: file coverage, relationship accuracy, and boundary coherence.

**Architecture:** New `core/representativeness.py` in architecture-model-standard computes three sub-scores by comparing model component `files` lists against manifest ground truth. New `architect_check` MCP tool in opencode-arch exposes this to the agent. The metric relies on `Component.files` being populated (by `create_components_from_manifest` or enrichment).

**Tech Stack:** Python 3.11+, architecture-model-standard (manifest + types), opencode-arch (MCP tools)

---

### Task 1: Create representativeness module with file coverage check

**Files:**
- Create: `src/architecture_model/core/representativeness.py`
- Test: `tests/test_representativeness.py`

**Step 1: Write the failing test**

```python
"""Tests for representativeness metric."""
import pytest
from architecture_model.core.types import Component, ArchitectureModel, Entities
from architecture_model.manifest.types import ModuleInfo, InterfaceEdge
from architecture_model.core.representativeness import compute_representativeness, RepresentativenessResult


def _make_model(components: list[Component]) -> ArchitectureModel:
    return ArchitectureModel(
        meta={"project": "test", "schema_version": "1.3"},
        entities=Entities(components=components),
        relationships=[],
    )


def _make_modules(files: list[str]) -> list[ModuleInfo]:
    return [
        ModuleInfo(file=f, line_count=50, functions=["fn"], classes=[], imports=[])
        for f in files
    ]


class TestFileCoverage:
    def test_perfect_coverage(self):
        """All manifest files appear in component.files."""
        model = _make_model([
            Component(id="C1", name="Core", status="ACTIVE", files=["core.py", "utils.py"]),
            Component(id="C2", name="CLI", status="ACTIVE", files=["cli.py"]),
        ])
        modules = _make_modules(["core.py", "utils.py", "cli.py"])
        result = compute_representativeness(model, modules, [])
        assert result.file_coverage == 100.0

    def test_partial_coverage(self):
        """One file missing from all components."""
        model = _make_model([
            Component(id="C1", name="Core", status="ACTIVE", files=["core.py"]),
        ])
        modules = _make_modules(["core.py", "utils.py"])
        result = compute_representativeness(model, modules, [])
        assert result.file_coverage == 50.0

    def test_trivial_files_excluded(self):
        """__init__.py with no code and __version__.py excluded from denominator."""
        model = _make_model([
            Component(id="C1", name="Core", status="ACTIVE", files=["core.py"]),
        ])
        modules = [
            ModuleInfo(file="core.py", line_count=50, functions=["fn"], classes=[], imports=[]),
            ModuleInfo(file="__init__.py", line_count=2, functions=[], classes=[], imports=[]),
            ModuleInfo(file="__version__.py", line_count=1, functions=[], classes=[], imports=[]),
        ]
        result = compute_representativeness(model, modules, [])
        assert result.file_coverage == 100.0  # trivial files don't count

    def test_empty_model_zero_coverage(self):
        """Model with no components and files in manifest = 0%."""
        model = _make_model([])
        modules = _make_modules(["core.py", "utils.py"])
        result = compute_representativeness(model, modules, [])
        assert result.file_coverage == 0.0
```

**Step 2: Run test to verify it fails**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_representativeness.py -v`
Expected: FAIL with ImportError (module doesn't exist yet)

**Step 3: Write minimal implementation**

```python
"""Representativeness metric: compare architecture model against code reality.

Three sub-scores:
1. File Coverage — % of source files mapped to components
2. Relationship Accuracy — % of model relationships backed by real imports
3. Boundary Coherence — avg cohesion of component file groupings

Overall = average of the three sub-scores.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel

from architecture_model.manifest.types import InterfaceEdge, ModuleInfo


_TRIVIAL_STEMS = {"__version__", "__main__"}


def _is_trivial_module(mod: ModuleInfo) -> bool:
    """Check if a module is trivial (excluded from coverage denominator)."""
    stem = PurePosixPath(mod.file).stem
    if stem in _TRIVIAL_STEMS:
        return True
    if stem == "__init__" and mod.line_count <= 5 and not mod.functions and not mod.classes:
        return True
    return False


@dataclass
class RepresentativenessResult:
    """Result of representativeness analysis."""
    file_coverage: float = 0.0  # 0-100
    relationship_accuracy: float = 0.0  # 0-100
    boundary_coherence: float = 0.0  # 0-100
    overall: float = 0.0  # 0-100

    # Details for debugging
    uncovered_files: list[str] = field(default_factory=list)
    unverified_relationships: list[str] = field(default_factory=list)
    low_coherence_components: list[str] = field(default_factory=list)


def compute_representativeness(
    model: "ArchitectureModel",
    modules: list[ModuleInfo],
    interfaces: list[InterfaceEdge],
) -> RepresentativenessResult:
    """Compute representativeness score for an architecture model.

    Args:
        model: The architecture model to evaluate.
        modules: Manifest modules (ground truth source files).
        interfaces: Manifest interface edges (ground truth imports).

    Returns:
        RepresentativenessResult with three sub-scores and overall.
    """
    result = RepresentativenessResult()

    # 1. File Coverage
    result.file_coverage, result.uncovered_files = _compute_file_coverage(model, modules)

    # 2. Relationship Accuracy
    result.relationship_accuracy, result.unverified_relationships = _compute_relationship_accuracy(model, interfaces)

    # 3. Boundary Coherence
    result.boundary_coherence, result.low_coherence_components = _compute_boundary_coherence(model, interfaces)

    # Overall
    result.overall = (result.file_coverage + result.relationship_accuracy + result.boundary_coherence) / 3

    return result


def _compute_file_coverage(
    model: "ArchitectureModel",
    modules: list[ModuleInfo],
) -> tuple[float, list[str]]:
    """Compute % of non-trivial source files mapped to components."""
    non_trivial = [m for m in modules if not _is_trivial_module(m)]
    if not non_trivial:
        return 100.0, []

    # Collect all files claimed by components
    components = model.entities.components if hasattr(model.entities, "components") else model.entities.get("components", []) if hasattr(model.entities, "get") else []
    covered: set[str] = set()
    for comp in components:
        for f in comp.files:
            covered.add(f)

    # Normalize paths for comparison
    manifest_files = {m.file for m in non_trivial}
    # Try matching with and without leading path segments
    matched = manifest_files & covered
    # Also try basename matching for flexibility
    covered_basenames = {PurePosixPath(f).name for f in covered}
    for mf in manifest_files - matched:
        if PurePosixPath(mf).name in covered_basenames:
            matched.add(mf)

    uncovered = sorted(manifest_files - matched)
    score = len(matched) / len(manifest_files) * 100

    return score, uncovered
```

**Step 4: Run test to verify it passes**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_representativeness.py::TestFileCoverage -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/architecture_model/core/representativeness.py tests/test_representativeness.py
git commit -m "feat: representativeness metric — file coverage sub-score"
```

---

### Task 2: Add relationship accuracy sub-score

**Files:**
- Modify: `src/architecture_model/core/representativeness.py`
- Test: `tests/test_representativeness.py`

**Step 1: Write the failing test**

```python
from architecture_model.core.types import Relationship


class TestRelationshipAccuracy:
    def test_all_relationships_verified(self):
        """Every depends_on relationship backed by import edge."""
        model = _make_model([
            Component(id="C1", name="Core", status="ACTIVE", files=["core.py"]),
            Component(id="C2", name="CLI", status="ACTIVE", files=["cli.py"]),
        ])
        model.relationships = [
            Relationship(from_id="C2", to_id="C1", type="depends_on"),
        ]
        interfaces = [InterfaceEdge(source="cli.py", target="core.py", import_path="core")]
        result = compute_representativeness(model, _make_modules(["core.py", "cli.py"]), interfaces)
        assert result.relationship_accuracy == 100.0

    def test_unverified_relationship(self):
        """Relationship in model but no matching import edge."""
        model = _make_model([
            Component(id="C1", name="Core", status="ACTIVE", files=["core.py"]),
            Component(id="C2", name="CLI", status="ACTIVE", files=["cli.py"]),
        ])
        model.relationships = [
            Relationship(from_id="C2", to_id="C1", type="depends_on"),
        ]
        interfaces = []  # No imports at all
        result = compute_representativeness(model, _make_modules(["core.py", "cli.py"]), interfaces)
        assert result.relationship_accuracy == 0.0
        assert len(result.unverified_relationships) == 1

    def test_no_relationships_is_100(self):
        """Model with no relationships = 100% (nothing to verify)."""
        model = _make_model([
            Component(id="C1", name="Core", status="ACTIVE", files=["core.py"]),
        ])
        result = compute_representativeness(model, _make_modules(["core.py"]), [])
        assert result.relationship_accuracy == 100.0
```

**Step 2: Run test to verify it fails**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_representativeness.py::TestRelationshipAccuracy -v`
Expected: FAIL (function returns 0.0 placeholder)

**Step 3: Implement relationship accuracy**

Add to `representativeness.py`:

```python
def _compute_relationship_accuracy(
    model: "ArchitectureModel",
    interfaces: list[InterfaceEdge],
) -> tuple[float, list[str]]:
    """Check % of model relationships backed by real import edges.

    For each depends_on/uses relationship, check if there's at least one
    import edge between any file in the source component and any file in
    the target component.
    """
    components = model.entities.components if hasattr(model.entities, "components") else model.entities.get("components", []) if hasattr(model.entities, "get") else []
    
    # Build component ID -> files mapping
    comp_files: dict[str, set[str]] = {}
    for comp in components:
        comp_files[comp.id] = set(comp.files)
        # Also add basename variants
        comp_files[comp.id].update(PurePosixPath(f).name for f in comp.files)

    # Build set of import edges (source_file -> target_file)
    import_edges: set[tuple[str, str]] = set()
    for edge in interfaces:
        import_edges.add((edge.source, edge.target))
        # Also add basenames
        import_edges.add((PurePosixPath(edge.source).name, PurePosixPath(edge.target).name))

    # Check each relationship
    verifiable_rels = [
        r for r in model.relationships
        if r.type in ("depends_on", "uses", "DEPENDS_ON", "USES")
        or (hasattr(r.type, 'value') and r.type.value in ("depends-on", "uses"))
    ]

    if not verifiable_rels:
        return 100.0, []

    verified = 0
    unverified: list[str] = []
    for rel in verifiable_rels:
        from_files = comp_files.get(rel.from_id, set())
        to_files = comp_files.get(rel.to_id, set())

        # Check if any import edge exists between the two file sets
        found = False
        for sf in from_files:
            for tf in to_files:
                if (sf, tf) in import_edges:
                    found = True
                    break
            if found:
                break

        if found:
            verified += 1
        else:
            unverified.append(f"{rel.from_id} → {rel.to_id}")

    score = verified / len(verifiable_rels) * 100
    return score, unverified
```

**Step 4: Run test to verify it passes**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_representativeness.py::TestRelationshipAccuracy -v`
Expected: PASS

**Step 5: Commit**

```bash
git add -A && git commit -m "feat: representativeness — relationship accuracy sub-score"
```

---

### Task 3: Add boundary coherence sub-score

**Files:**
- Modify: `src/architecture_model/core/representativeness.py`
- Test: `tests/test_representativeness.py`

**Step 1: Write the failing test**

```python
class TestBoundaryCoherence:
    def test_perfect_coherence_single_file_components(self):
        """Single-file components always have 100% coherence."""
        model = _make_model([
            Component(id="C1", name="Core", status="ACTIVE", files=["core.py"]),
            Component(id="C2", name="CLI", status="ACTIVE", files=["cli.py"]),
        ])
        interfaces = [InterfaceEdge(source="cli.py", target="core.py", import_path="core")]
        result = compute_representativeness(model, _make_modules(["core.py", "cli.py"]), interfaces)
        assert result.boundary_coherence == 100.0

    def test_high_coherence_internal_imports(self):
        """Multi-file component where files import each other more than outsiders."""
        model = _make_model([
            Component(id="C1", name="Core", status="ACTIVE", files=["core.py", "types.py", "utils.py"]),
            Component(id="C2", name="CLI", status="ACTIVE", files=["cli.py"]),
        ])
        interfaces = [
            # 2 internal edges within Core
            InterfaceEdge(source="core.py", target="types.py", import_path="types"),
            InterfaceEdge(source="core.py", target="utils.py", import_path="utils"),
            # 1 external edge
            InterfaceEdge(source="cli.py", target="core.py", import_path="core"),
        ]
        modules = _make_modules(["core.py", "types.py", "utils.py", "cli.py"])
        result = compute_representativeness(model, modules, interfaces)
        # Core has 2 internal, 1 external → cohesion = 2/3 = 66.7%
        # CLI has 0 internal, 1 external (single file) → 100%
        # Average = (66.7 + 100) / 2 = 83.3%
        assert 83.0 <= result.boundary_coherence <= 84.0

    def test_low_coherence_wrong_grouping(self):
        """Files grouped together that don't import each other."""
        model = _make_model([
            Component(id="C1", name="Bad", status="ACTIVE", files=["a.py", "b.py"]),
        ])
        interfaces = [
            # Only external: a.py imports something outside, b.py imports something outside
            InterfaceEdge(source="a.py", target="external.py", import_path="ext"),
            InterfaceEdge(source="b.py", target="external.py", import_path="ext"),
        ]
        modules = _make_modules(["a.py", "b.py", "external.py"])
        result = compute_representativeness(model, modules, interfaces)
        # C1 has 0 internal edges, 2 external edges → cohesion = 0%
        assert result.boundary_coherence < 50.0
        assert "Bad" in result.low_coherence_components
```

**Step 2: Run test to verify it fails**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_representativeness.py::TestBoundaryCoherence -v`
Expected: FAIL

**Step 3: Implement boundary coherence**

```python
def _compute_boundary_coherence(
    model: "ArchitectureModel",
    interfaces: list[InterfaceEdge],
) -> tuple[float, list[str]]:
    """Compute average cohesion of component groupings.

    For each multi-file component:
      internal_edges = import edges between files within the component
      external_edges = import edges from/to component files involving other components
      cohesion = internal / (internal + external) if any edges, else 1.0

    Single-file components get 1.0 by default.
    """
    components = model.entities.components if hasattr(model.entities, "components") else model.entities.get("components", []) if hasattr(model.entities, "get") else []

    if not components:
        return 100.0, []

    # Build file -> component mapping
    file_to_comp: dict[str, str] = {}
    for comp in components:
        for f in comp.files:
            file_to_comp[f] = comp.id
            file_to_comp[PurePosixPath(f).name] = comp.id

    cohesion_scores: list[tuple[str, float]] = []

    for comp in components:
        if len(comp.files) <= 1:
            cohesion_scores.append((comp.name, 1.0))
            continue

        comp_file_set = set(comp.files) | {PurePosixPath(f).name for f in comp.files}
        internal = 0
        external = 0

        for edge in interfaces:
            src_in = edge.source in comp_file_set or PurePosixPath(edge.source).name in comp_file_set
            tgt_in = edge.target in comp_file_set or PurePosixPath(edge.target).name in comp_file_set

            if src_in and tgt_in:
                internal += 1
            elif src_in or tgt_in:
                external += 1

        total = internal + external
        if total == 0:
            cohesion_scores.append((comp.name, 1.0))
        else:
            cohesion_scores.append((comp.name, internal / total))

    low_coherence = [name for name, score in cohesion_scores if score < 0.5]
    avg = sum(s for _, s in cohesion_scores) / len(cohesion_scores) * 100

    return avg, low_coherence
```

**Step 4: Run test to verify it passes**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_representativeness.py::TestBoundaryCoherence -v`
Expected: PASS

**Step 5: Commit**

```bash
git add -A && git commit -m "feat: representativeness — boundary coherence sub-score"
```

---

### Task 4: Add overall score test and export

**Files:**
- Modify: `tests/test_representativeness.py`
- Modify: `src/architecture_model/core/__init__.py` (if exists) or `src/architecture_model/__init__.py`

**Step 1: Write the test**

```python
class TestOverall:
    def test_overall_is_average_of_three(self):
        """Overall = (file_coverage + relationship_accuracy + boundary_coherence) / 3."""
        model = _make_model([
            Component(id="C1", name="Core", status="ACTIVE", files=["core.py"]),
        ])
        modules = _make_modules(["core.py"])
        result = compute_representativeness(model, modules, [])
        expected = (result.file_coverage + result.relationship_accuracy + result.boundary_coherence) / 3
        assert abs(result.overall - expected) < 0.01

    def test_perfect_model_gets_100(self):
        """A perfectly representative model scores 100 overall."""
        model = _make_model([
            Component(id="C1", name="Core", status="ACTIVE", files=["core.py", "utils.py"]),
            Component(id="C2", name="CLI", status="ACTIVE", files=["cli.py"]),
        ])
        model.relationships = [
            Relationship(from_id="C2", to_id="C1", type="depends_on"),
        ]
        modules = _make_modules(["core.py", "utils.py", "cli.py"])
        interfaces = [
            InterfaceEdge(source="core.py", target="utils.py", import_path="utils"),
            InterfaceEdge(source="cli.py", target="core.py", import_path="core"),
        ]
        result = compute_representativeness(model, modules, interfaces)
        assert result.file_coverage == 100.0
        assert result.relationship_accuracy == 100.0
        assert result.boundary_coherence == 100.0
        assert result.overall == 100.0
```

**Step 2: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_representativeness.py -v`
Expected: All PASS

**Step 3: Add export to top-level __init__.py**

In `src/architecture_model/__init__.py`, add:
```python
from architecture_model.core.representativeness import compute_representativeness, RepresentativenessResult
```

And add to `__all__`:
```python
"compute_representativeness",
"RepresentativenessResult",
```

**Step 4: Verify export works**

Run: `/opt/anaconda3/bin/python -c "from architecture_model import compute_representativeness, RepresentativenessResult; print('OK')"`
Expected: OK

**Step 5: Commit**

```bash
git add -A && git commit -m "feat: export representativeness metric from top-level"
```

---

### Task 5: Create architect_check MCP tool in opencode-arch

**Files:**
- Create: `src/opencode_arch/mcp/tools/check.py`
- Modify: `src/opencode_arch/mcp/server.py`
- Test: `tests/test_check_tool.py`

**Step 1: Write the failing test**

```python
"""Tests for architect_check MCP tool."""
import pytest
from opencode_arch.mcp.tools.check import check_representativeness


@pytest.mark.asyncio
async def test_check_nonexistent_path():
    result = await check_representativeness(repo_path="/nonexistent", model_yaml="meta: {}")
    assert "error" in result


@pytest.mark.asyncio
async def test_check_returns_scores(tmp_path):
    # Create a minimal project
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text("class Core:\n    def run(self): pass\n")
    (pkg / "cli.py").write_text("from pkg import core\n\ndef main(): pass\n")

    model_yaml = """
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: C1
      name: Core
      status: ACTIVE
      files: [pkg/core.py]
    - id: C2
      name: CLI
      status: ACTIVE
      files: [pkg/cli.py]
relationships:
  - from: C2
    to: C1
    type: depends_on
"""
    result = await check_representativeness(repo_path=str(tmp_path), model_yaml=model_yaml)
    assert "error" not in result
    assert "file_coverage" in result
    assert "relationship_accuracy" in result
    assert "boundary_coherence" in result
    assert "overall" in result
    assert 0 <= result["overall"] <= 100


@pytest.mark.asyncio
async def test_check_reports_uncovered_files(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text("class Core:\n    def run(self): pass\n")
    (pkg / "orphan.py").write_text("class Orphan:\n    def lost(self): pass\n")

    model_yaml = """
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: C1
      name: Core
      status: ACTIVE
      files: [pkg/core.py]
relationships: []
"""
    result = await check_representativeness(repo_path=str(tmp_path), model_yaml=model_yaml)
    assert result["file_coverage"] < 100.0
    assert len(result["uncovered_files"]) >= 1
```

**Step 2: Run test to verify it fails**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_check_tool.py -v`
Expected: FAIL (module doesn't exist)

**Step 3: Implement the tool**

Create `src/opencode_arch/mcp/tools/check.py`:

```python
"""architect_check MCP tool — verify model representativeness against code reality."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


async def check_representativeness(repo_path: str, model_yaml: str) -> dict[str, Any]:
    """Check how well an architecture model represents the actual codebase.

    Computes three mechanical sub-scores:
    1. File Coverage — % of source files mapped to components
    2. Relationship Accuracy — % of model relationships backed by real imports
    3. Boundary Coherence — avg internal cohesion of component groupings

    Args:
        repo_path: Absolute path to the repository root.
        model_yaml: The architecture model YAML to evaluate.

    Returns:
        Dict with scores, details, and suggested improvements.
    """
    path = Path(repo_path)
    if not path.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}

    try:
        from architecture_model.manifest.generator import generate_manifest
        from architecture_model.core.parser import load_model_from_string
        from architecture_model.core.representativeness import compute_representativeness

        # Generate ground truth manifest
        manifest = generate_manifest(path)

        # Parse the model
        model = load_model_from_string(model_yaml)

        # Compute representativeness
        result = compute_representativeness(model, manifest.modules, manifest.interfaces)

        output = {
            "file_coverage": round(result.file_coverage, 1),
            "relationship_accuracy": round(result.relationship_accuracy, 1),
            "boundary_coherence": round(result.boundary_coherence, 1),
            "overall": round(result.overall, 1),
            "uncovered_files": result.uncovered_files,
            "unverified_relationships": result.unverified_relationships,
            "low_coherence_components": result.low_coherence_components,
        }

        try:
            from opencode_arch.telemetry.collector import drain_and_store
            drain_and_store(tool="architect_check", repo=path.name)
        except Exception:
            pass

        return output

    except Exception as e:
        return {"error": f"Check failed: {e}"}
```

**Step 4: Register in server.py**

Add to `src/opencode_arch/mcp/server.py`:
```python
from opencode_arch.mcp.tools.check import check_representativeness

@mcp.tool()
async def architect_check(repo_path: str, model_yaml: str) -> dict:
    """Verify model representativeness against code reality.

    Computes three mechanical sub-scores comparing the model against
    AST-derived ground truth. Target: 100% on all three.

    Returns: file_coverage, relationship_accuracy, boundary_coherence, overall (0-100).
    """
    return await check_representativeness(repo_path=repo_path, model_yaml=model_yaml)
```

**Step 5: Handle `load_model_from_string`**

We need to check if `load_model_from_string` exists. If not, use `yaml.safe_load` + `parse_model_dict`. Check `core/parser.py` for available functions and use the appropriate one. Likely pattern:
```python
import yaml
raw = yaml.safe_load(model_yaml)
from architecture_model.core.parser import _parse_model_dict  # or load_model with temp file
```

Alternative: write to a temp file and use `load_model(tmp_path)`.

**Step 6: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_check_tool.py -v`
Expected: All PASS

**Step 7: Commit**

```bash
git add -A && git commit -m "feat: architect_check MCP tool — verify model representativeness"
```

---

### Task 6: Integration test on real repo

**Files:**
- Create: `tests/test_representativeness_integration.py` (in architecture-model-standard)

**Step 1: Write integration test**

```python
"""Integration test: representativeness on self (architecture-model-standard)."""
import pytest
from pathlib import Path
from architecture_model.manifest.generator import generate_manifest
from architecture_model.manifest.grouping import create_components_from_manifest
from architecture_model.core.types import ArchitectureModel, Entities
from architecture_model.core.representativeness import compute_representativeness


@pytest.mark.skipif(
    not Path("/Users/baigm2/Documents/Projects/architecture-model-standard/src").exists(),
    reason="Requires local repo"
)
class TestRepresentativenessOnSelf:
    def test_grouped_model_has_high_file_coverage(self):
        """Model built from create_components_from_manifest covers all files."""
        root = Path("/Users/baigm2/Documents/Projects/architecture-model-standard")
        manifest = generate_manifest(root)
        components = create_components_from_manifest(manifest)
        model = ArchitectureModel(
            meta={"project": "arch-std", "schema_version": "1.3"},
            entities=Entities(components=components),
            relationships=[],
        )
        result = compute_representativeness(model, manifest.modules, manifest.interfaces)
        # create_components_from_manifest should give 100% file coverage
        assert result.file_coverage == 100.0

    def test_overall_above_80(self):
        """Grouped model should score at least 80% overall."""
        root = Path("/Users/baigm2/Documents/Projects/architecture-model-standard")
        manifest = generate_manifest(root)
        components = create_components_from_manifest(manifest)
        model = ArchitectureModel(
            meta={"project": "arch-std", "schema_version": "1.3"},
            entities=Entities(components=components),
            relationships=[],
        )
        result = compute_representativeness(model, manifest.modules, manifest.interfaces)
        # With no relationships, relationship_accuracy = 100% (nothing to verify)
        # File coverage = 100%, boundary coherence should be decent
        assert result.overall >= 80.0
```

**Step 2: Run**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_representativeness_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add -A && git commit -m "test: representativeness integration test on self"
```

---

### Task 7: Update CONTEXT.md and extraction skill

**Files:**
- Modify: `CONTEXT.md` (opencode-arch) — add architect_check tool description
- Modify: `skills/extraction/SKILL.md` — add check step after extract
- Modify: `opencode.json` — add 7th tool

**Step 1: Update CONTEXT.md**

Add after architect_group section:
```markdown
### 7. `architect_check(repo_path: str, model_yaml: str) -> dict`
Verifies model representativeness against code reality.

**Returns:** `{file_coverage, relationship_accuracy, boundary_coherence, overall, uncovered_files, unverified_relationships, low_coherence_components}`

**When to use:** After extraction — verify the model is 100% representative before accepting it.
```

**Step 2: Update extraction skill**

Add step 7 after Store:
```markdown
7. **Check**: Call `architect_check(repo_path, model_yaml)` to verify representativeness.
   - Target: 100% on all three sub-scores.
   - If file_coverage < 100%: add uncovered files to appropriate components.
   - If relationship_accuracy < 100%: verify unverified relationships or remove them.
   - If boundary_coherence < 100%: consider re-grouping low-coherence components.
```

**Step 3: Update opencode.json**

Add to tools array:
```json
{
  "name": "architect_check",
  "description": "Verify model representativeness against code reality. Returns file coverage, relationship accuracy, and boundary coherence scores (target: 100%)."
}
```

**Step 4: Commit**

```bash
git add -A && git commit -m "docs: add architect_check to CONTEXT.md, skill, and opencode.json"
```

---

### Task 8: Final verification

**Step 1: Run all arch-std tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/ --ignore=tests/test_config_loader.py -q`
Expected: 650+ passed, 0 failures

**Step 2: Run all opencode-arch tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/ -q` (from opencode-arch dir)
Expected: 278+ passed (excluding pre-existing failures)

**Step 3: End-to-end verification**

```python
/opt/anaconda3/bin/python -c "
import asyncio
from opencode_arch.mcp.tools.check import check_representativeness
from opencode_arch.mcp.tools.group import group_repository

# Group opencode-arch
groups = asyncio.run(group_repository('/Users/baigm2/Documents/Projects/opencode-arch'))
print(f'Groups: {groups[\"total_groups\"]}')

# Build model YAML from groups and check
# (This verifies the full pipeline works)
"
```

**Step 4: Commit and tag**

```bash
# In architecture-model-standard:
git tag v0.4.1

# In opencode-arch:
git tag v0.4.1
```
