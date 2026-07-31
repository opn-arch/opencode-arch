# Recursive Deep Decomposition Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Recursively decompose F-block components into internal sub-components using import-graph clustering, then have the agent name them. Produces hierarchical sub-models (system-of-systems) until all leaves have <N modules.

**Architecture:** New `orchestration/deep_decompose.py` that takes a block manifest, builds an import graph, clusters modules into groups, produces sub-components with `contains` relationships. Recurses on groups that exceed a threshold. Agent names clusters post-hoc via manifest context.

**Tech Stack:** Python 3.11+, existing `derive_interfaces` for edges, new clustering with target-k support, `ArchitectureModel` for output.

**Working directory:** `/Users/baigm2/Documents/Projects/architecture-model-standard`
**Python:** `/opt/anaconda3/bin/python`
**Run tests:** `pytest tests/ --ignore=tests/test_config_loader.py -q`

---

## Design

### Data Flow

```
Block manifest (55 modules, interface edges)
  → Build import graph (adjacency matrix from derive_interfaces)
  → Cluster modules into 3-6 groups (greedy modularity with target_k)
  → Each cluster becomes a sub-component:
      - ID: COMP-<PARENT>-<INDEX> (temporary, agent renames)
      - files: modules in cluster
      - internal relationships from import edges within cluster
      - boundary relationships from edges crossing clusters
  → If any cluster has >threshold modules, recurse
  → Output: DecomposeResult with hierarchical sub-components + relationships
```

### Clustering Algorithm

Adapt `auto_assign_f_blocks` to support `target_k` (target number of clusters) instead of just `max_cluster_size`. Algorithm:
1. Build undirected adjacency from import edges
2. Compute `max_cluster_size = ceil(num_modules / target_k)`
3. Seed clusters from highest-degree nodes
4. Grow by adjacency affinity (shared neighbors)
5. Post-process: merge clusters smaller than `min_cluster_size` into nearest neighbor

### Recursion

```python
def deep_decompose_block(manifest, *, target_k=5, min_modules=3, max_modules=15):
    """
    If len(modules) <= max_modules: return as leaf (no decomposition)
    Else: cluster into target_k groups, recurse on groups > max_modules
    """
```

### Threshold Defaults
- `max_modules = 15` — decompose if block has more than this
- `target_k = 5` — aim for ~5 sub-components per level
- `min_modules = 3` — don't create tiny groups (merge into neighbors)

### Agent Naming Step

After clustering produces `[COMP-F6-1, COMP-F6-2, ...]`, the pipeline exposes a `format_naming_context(result)` function that formats a compact summary (file stems + top classes per cluster) suitable for the agent to assign semantic names.

---

## Tasks

### Task 1: Module-level clustering function

Create `src/architecture_model/core/cluster.py` with a function that takes modules + edges and returns groups.

**Files:**
- Create: `src/architecture_model/core/cluster.py`
- Create: `tests/test_cluster.py`

**Step 1: Write failing test**

```python
"""Tests for module-level import-graph clustering."""
from architecture_model.core.cluster import cluster_modules


def test_clusters_connected_modules_together():
    """Modules with import edges between them land in the same cluster."""
    modules = ["a.py", "b.py", "c.py", "d.py", "e.py", "f.py"]
    # Two clear groups: (a,b,c) import each other, (d,e,f) import each other
    edges = [
        ("a.py", "b.py"), ("b.py", "c.py"), ("a.py", "c.py"),
        ("d.py", "e.py"), ("e.py", "f.py"), ("d.py", "f.py"),
    ]
    groups = cluster_modules(modules, edges, target_k=2)
    assert len(groups) == 2
    group_sets = [set(g) for g in groups]
    assert {"a.py", "b.py", "c.py"} in group_sets
    assert {"d.py", "e.py", "f.py"} in group_sets


def test_target_k_respected():
    """Clustering produces approximately target_k groups."""
    modules = [f"mod{i}.py" for i in range(20)]
    edges = [(f"mod{i}.py", f"mod{i+1}.py") for i in range(19)]
    groups = cluster_modules(modules, edges, target_k=4)
    assert 3 <= len(groups) <= 5


def test_isolated_modules_get_assigned():
    """Modules with no edges get merged into a group."""
    modules = ["a.py", "b.py", "c.py", "isolated.py"]
    edges = [("a.py", "b.py"), ("b.py", "c.py")]
    groups = cluster_modules(modules, edges, target_k=2)
    all_assigned = set()
    for g in groups:
        all_assigned.update(g)
    assert "isolated.py" in all_assigned


def test_min_cluster_size_merges_tiny_groups():
    """Groups smaller than min_cluster_size get merged into neighbors."""
    modules = ["a.py", "b.py", "c.py", "d.py", "e.py", "tiny.py"]
    edges = [
        ("a.py", "b.py"), ("b.py", "c.py"),
        ("d.py", "e.py"),
        ("tiny.py", "a.py"),
    ]
    groups = cluster_modules(modules, edges, target_k=2, min_cluster_size=2)
    for g in groups:
        if "a.py" in g:
            assert "tiny.py" in g
            break
```

**Step 2:** Run: `pytest tests/test_cluster.py -v` — expect FAIL (ImportError)

**Step 3: Implement `src/architecture_model/core/cluster.py`**

```python
"""Module-level import-graph clustering.

Groups modules by import affinity using greedy modularity clustering
with support for target cluster count and minimum group size.
"""
from __future__ import annotations

from collections import defaultdict
from math import ceil


def cluster_modules(
    modules: list[str],
    edges: list[tuple[str, str]],
    *,
    target_k: int = 5,
    min_cluster_size: int = 3,
) -> list[list[str]]:
    """Cluster modules into groups by import-graph affinity.

    Args:
        modules: List of module file paths.
        edges: List of (source, target) import edges.
        target_k: Target number of clusters.
        min_cluster_size: Merge clusters smaller than this.

    Returns:
        List of module groups (each group is a list of file paths).
    """
    if len(modules) <= target_k:
        return [[m] for m in modules]

    max_cluster_size = ceil(len(modules) / target_k)

    # Build undirected adjacency
    adj: dict[str, set[str]] = defaultdict(set)
    module_set = set(modules)
    for src, tgt in edges:
        if src in module_set and tgt in module_set:
            adj[src].add(tgt)
            adj[tgt].add(src)

    # Sort by degree (most connected first = cluster seeds)
    sorted_modules = sorted(modules, key=lambda m: len(adj.get(m, set())), reverse=True)

    assigned: dict[str, int] = {}
    clusters: list[list[str]] = []

    for mod in sorted_modules:
        if mod in assigned:
            continue
        idx = len(clusters)
        cluster = [mod]
        assigned[mod] = idx

        # Grow by adding adjacent unassigned, preferring shared neighbors
        candidates = sorted(
            [n for n in adj.get(mod, set()) if n not in assigned],
            key=lambda n: len(adj.get(n, set()) & adj.get(mod, set())),
            reverse=True,
        )
        for candidate in candidates:
            if candidate in assigned:
                continue
            if len(cluster) >= max_cluster_size:
                break
            cluster.append(candidate)
            assigned[candidate] = idx

        clusters.append(cluster)

    # Assign unassigned (isolated) modules to nearest cluster
    for mod in modules:
        if mod not in assigned:
            merged = False
            for src, tgt in edges:
                if src == mod and tgt in assigned:
                    clusters[assigned[tgt]].append(mod)
                    assigned[mod] = assigned[tgt]
                    merged = True
                    break
                if tgt == mod and src in assigned:
                    clusters[assigned[src]].append(mod)
                    assigned[mod] = assigned[src]
                    merged = True
                    break
            if not merged:
                smallest = min(range(len(clusters)), key=lambda i: len(clusters[i]))
                clusters[smallest].append(mod)
                assigned[mod] = smallest

    # Merge tiny clusters into nearest neighbor
    merged_clusters: list[list[str]] = []
    for cluster in clusters:
        if len(cluster) >= min_cluster_size:
            merged_clusters.append(cluster)
        else:
            cluster_set = set(cluster)
            best_target = None
            best_score = -1
            for i, other in enumerate(merged_clusters):
                other_set = set(other)
                score = sum(
                    1 for src, tgt in edges
                    if (src in cluster_set and tgt in other_set)
                    or (tgt in cluster_set and src in other_set)
                )
                if score > best_score:
                    best_score = score
                    best_target = i
            if best_target is not None:
                merged_clusters[best_target].extend(cluster)
            elif merged_clusters:
                merged_clusters[0].extend(cluster)
            else:
                merged_clusters.append(cluster)

    return merged_clusters
```

**Step 4:** Run: `pytest tests/test_cluster.py -v` — expect PASS
**Step 5:** Run full suite, commit: `git commit -m "feat: module-level import-graph clustering (cluster_modules)"`

---

### Task 2: Deep decomposition function

**Files:**
- Create: `src/architecture_model/orchestration/deep_decompose.py`
- Create: `tests/test_deep_decompose.py`

**Step 1: Write failing test**

```python
"""Tests for recursive deep decomposition."""
from pathlib import Path

from architecture_model.orchestration.deep_decompose import (
    deep_decompose_block,
    DecomposeResult,
)
from architecture_model.manifest.recursive import generate_block_manifest


def _create_block_with_modules(tmp_path, n_modules=20, n_groups=4):
    """Create a block with n_modules arranged in n_groups of import clusters."""
    pkg = tmp_path / "myapp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")

    group_size = n_modules // n_groups
    for g in range(n_groups):
        subpkg = pkg / f"group{g}"
        subpkg.mkdir()
        (subpkg / "__init__.py").write_text("")
        for i in range(group_size):
            imports = f"from myapp.group{g}.mod{max(0,i-1)} import something\n" if i > 0 else ""
            content = f'"""Module {g}_{i}."""\n{imports}class Class{g}_{i}:\n    pass\n' + "\n" * 50
            (subpkg / f"mod{i}.py").write_text(content)

    # Cross-group: each group's first module imports from group0
    for g in range(1, n_groups):
        existing = (pkg / f"group{g}" / "mod0.py").read_text()
        (pkg / f"group{g}" / "mod0.py").write_text(
            f"from myapp.group0.mod0 import Class0_0\n" + existing
        )

    return pkg


def test_deep_decompose_produces_sub_components(tmp_path):
    """Deep decomposition breaks a large block into sub-components."""
    pkg = _create_block_with_modules(tmp_path, n_modules=20, n_groups=4)
    block_def = {"name": "MyBlock", "dirs": ["myapp"], "files": []}
    manifest = generate_block_manifest(tmp_path, "F1", block_def)

    result = deep_decompose_block(manifest, block_id="F1", block_name="MyBlock")

    assert isinstance(result, DecomposeResult)
    assert len(result.sub_components) >= 2
    assert len(result.sub_components) <= 8
    # All non-init modules accounted for
    all_files = set()
    for sc in result.sub_components:
        all_files.update(sc.files)
    manifest_files = {m.file for m in manifest.modules if "__init__" not in m.file}
    assert manifest_files.issubset(all_files)


def test_deep_decompose_skips_small_blocks(tmp_path):
    """Blocks with few modules don't get decomposed."""
    pkg = tmp_path / "small"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for i in range(5):
        (pkg / f"mod{i}.py").write_text(f'"""M{i}."""\nclass C{i}: pass\n' + "\n" * 50)

    block_def = {"name": "Small", "dirs": ["small"], "files": []}
    manifest = generate_block_manifest(tmp_path, "F1", block_def)

    result = deep_decompose_block(manifest, block_id="F1", block_name="Small")
    assert result.sub_components == []


def test_deep_decompose_produces_relationships(tmp_path):
    """Sub-components have dependency relationships between them."""
    pkg = _create_block_with_modules(tmp_path, n_modules=20, n_groups=4)
    block_def = {"name": "MyBlock", "dirs": ["myapp"], "files": []}
    manifest = generate_block_manifest(tmp_path, "F1", block_def)

    result = deep_decompose_block(manifest, block_id="F1", block_name="MyBlock")
    assert len(result.internal_relationships) > 0
```

**Step 2:** Run: `pytest tests/test_deep_decompose.py -v` — expect FAIL

**Step 3: Implement `src/architecture_model/orchestration/deep_decompose.py`**

```python
"""Recursive deep decomposition of a block into sub-components.

Takes a block manifest (modules + import edges) and clusters modules
into sub-components using import-graph affinity. Recurses on large clusters.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from architecture_model.core.cluster import cluster_modules
from architecture_model.manifest.interfaces import derive_interfaces
from architecture_model.manifest.types import Manifest

logger = logging.getLogger(__name__)


@dataclass
class SubComponent:
    """A sub-component produced by decomposition."""
    id: str
    name: str
    files: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    line_count: int = 0


@dataclass
class InternalRelationship:
    """A dependency between two sub-components."""
    from_id: str
    to_id: str
    edge_count: int = 1


@dataclass
class DecomposeResult:
    """Result of deep decomposition."""
    block_id: str
    block_name: str
    sub_components: list[SubComponent] = field(default_factory=list)
    internal_relationships: list[InternalRelationship] = field(default_factory=list)
    depth: int = 1


def deep_decompose_block(
    manifest: Manifest,
    *,
    block_id: str,
    block_name: str,
    max_modules: int = 15,
    target_k: int = 5,
    min_cluster_size: int = 3,
    parent_id: str = "",
) -> DecomposeResult:
    """Decompose a block manifest into sub-components via import clustering.

    Args:
        manifest: Block manifest with modules and their imports.
        block_id: F-block ID (e.g., "F6").
        block_name: Human name (e.g., "Integration MQTT").
        max_modules: Don't decompose if fewer modules than this.
        target_k: Target number of sub-components.
        min_cluster_size: Merge clusters smaller than this.
        parent_id: Parent component ID prefix for naming.

    Returns:
        DecomposeResult with sub_components and internal_relationships.
        Empty sub_components if block is too small to decompose.
    """
    result = DecomposeResult(block_id=block_id, block_name=block_name)

    # Filter __init__.py (not meaningful standalone)
    modules = [m for m in manifest.modules if Path(m.file).stem != "__init__"]

    if len(modules) <= max_modules:
        return result

    # Build edges from derive_interfaces
    edges_raw = derive_interfaces(modules, Path(manifest.project_root or "."))
    edges = [(e.source, e.target) for e in edges_raw]
    module_files = [m.file for m in modules]

    # Cluster
    groups = cluster_modules(module_files, edges, target_k=target_k, min_cluster_size=min_cluster_size)

    # Build sub-components
    comp_prefix = parent_id or f"COMP-{block_id}"
    file_to_module = {m.file: m for m in modules}

    for i, group in enumerate(groups, 1):
        comp_id = f"{comp_prefix}-{i}"
        classes = []
        functions = []
        line_count = 0
        for f in group:
            mod = file_to_module.get(f)
            if mod:
                classes.extend(c.name for c in mod.classes)
                functions.extend(fn.name for fn in mod.functions)
                line_count += mod.line_count

        result.sub_components.append(SubComponent(
            id=comp_id,
            name=f"{block_name} Sub-{i}",
            files=group,
            classes=classes,
            functions=functions,
            line_count=line_count,
        ))

    # Internal relationships (edges crossing sub-component boundaries)
    file_to_comp: dict[str, str] = {}
    for sc in result.sub_components:
        for f in sc.files:
            file_to_comp[f] = sc.id

    rel_counts: dict[tuple[str, str], int] = {}
    for src, tgt in edges:
        src_comp = file_to_comp.get(src)
        tgt_comp = file_to_comp.get(tgt)
        if src_comp and tgt_comp and src_comp != tgt_comp:
            key = (src_comp, tgt_comp)
            rel_counts[key] = rel_counts.get(key, 0) + 1

    for (from_id, to_id), count in rel_counts.items():
        result.internal_relationships.append(
            InternalRelationship(from_id=from_id, to_id=to_id, edge_count=count)
        )

    return result
```

**Step 4:** Verify passes + full suite
**Step 5:** Commit: `git commit -m "feat: deep_decompose_block — recursive sub-component decomposition"`

---

### Task 3: Integrate into pipeline

**Files:**
- Modify: `src/architecture_model/orchestration/pipeline.py`
- Modify: `tests/test_pipeline.py`

**Step 1: Write failing test**

```python
def test_run_pipeline_deep_decompose(tmp_path):
    """Pipeline with deep=True produces sub-components for large blocks."""
    pkg = tmp_path / "bigpkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for i in range(20):
        imports = f"from bigpkg.mod{max(0,i-1)} import something\n" if i > 0 else ""
        (pkg / f"mod{i}.py").write_text(
            f'"""Module {i}."""\n{imports}class Cls{i}:\n    pass\n' + "\n" * 50
        )

    (tmp_path / ".architecture-model.yaml").write_text(
        "functional_blocks:\n"
        "  F1:\n"
        "    name: BigPackage\n"
        "    dirs:\n"
        "      - bigpkg\n"
        "    files: []\n"
    )

    result = run_pipeline(tmp_path, deep=True)
    assert "F1" in result.deep_decompositions
    decomp = result.deep_decompositions["F1"]
    assert len(decomp.sub_components) >= 2
```

**Step 2:** Verify fails

**Step 3:** Add to pipeline:
- Add `deep: bool = False` parameter to `run_pipeline`
- Add `deep_decompositions: dict[str, DecomposeResult]` field to `PipelineResult`
- After Step 1 (manifests), if `deep=True`, run `deep_decompose_block()` on each block manifest
- Write decomposition summary to `.architecture-models/<block>/decomposition.yaml`

**Step 4:** Verify + full suite
**Step 5:** Commit: `git commit -m "feat: integrate deep decomposition into pipeline (deep=True)"`

---

### Task 4: Context formatter for agent naming

**Files:**
- Create: `src/architecture_model/orchestration/naming_context.py`
- Create: `tests/test_naming_context.py`

**Step 1: Write failing test**

```python
"""Tests for decomposition naming context formatter."""
from architecture_model.orchestration.naming_context import format_naming_context
from architecture_model.orchestration.deep_decompose import DecomposeResult, SubComponent, InternalRelationship


def test_format_naming_context_compact():
    """Naming context is compact and informative."""
    result = DecomposeResult(
        block_id="F6",
        block_name="MQTT Integration",
        sub_components=[
            SubComponent(id="COMP-F6-1", name="temp", files=["mqtt/client.py", "mqtt/transport.py"],
                        classes=["MQTT", "MqttClientSetup", "AsyncTransport"], functions=["connect", "disconnect"], line_count=800),
            SubComponent(id="COMP-F6-2", name="temp", files=["mqtt/discovery.py", "mqtt/models.py"],
                        classes=["MqttDiscovery", "DiscoveryPayload"], functions=["async_start", "process_message"], line_count=600),
        ],
        internal_relationships=[
            InternalRelationship(from_id="COMP-F6-2", to_id="COMP-F6-1", edge_count=5),
        ],
    )

    context = format_naming_context(result)
    assert "COMP-F6-1" in context
    assert "MQTT" in context
    assert "client" in context
    assert len(context) < 2000


def test_format_naming_context_empty():
    """Empty decomposition produces minimal output."""
    result = DecomposeResult(block_id="F1", block_name="Core")
    context = format_naming_context(result)
    assert "no sub-components" in context.lower() or context.strip() == ""
```

**Step 2:** Verify fails

**Step 3: Implement `src/architecture_model/orchestration/naming_context.py`**

```python
"""Format decomposition results as compact context for agent naming."""
from __future__ import annotations

from architecture_model.orchestration.deep_decompose import DecomposeResult


def format_naming_context(result: DecomposeResult) -> str:
    """Format a DecomposeResult for the agent to assign semantic names.

    Returns a compact markdown-like string showing each cluster's
    key files, classes, and inter-cluster dependencies.
    """
    if not result.sub_components:
        return f"{result.block_name}: no sub-components (below threshold)"

    lines = [f"## {result.block_name} ({result.block_id}) — {len(result.sub_components)} sub-components\n"]

    for sc in result.sub_components:
        stems = [f.rsplit("/", 1)[-1].removesuffix(".py") for f in sc.files[:8]]
        extra = f" +{len(sc.files) - 8} more" if len(sc.files) > 8 else ""
        top_classes = sc.classes[:6]
        top_funcs = sc.functions[:4]
        lines.append(f"### {sc.id} ({sc.line_count} lines, {len(sc.files)} files)")
        lines.append(f"  Files: {', '.join(stems)}{extra}")
        if top_classes:
            lines.append(f"  Classes: {', '.join(top_classes)}")
        if top_funcs:
            lines.append(f"  Functions: {', '.join(top_funcs)}")
        lines.append("")

    if result.internal_relationships:
        lines.append("### Dependencies")
        for rel in sorted(result.internal_relationships, key=lambda r: -r.edge_count):
            lines.append(f"  {rel.from_id} → {rel.to_id} ({rel.edge_count} imports)")

    return "\n".join(lines)
```

**Step 4:** Verify + full suite
**Step 5:** Commit: `git commit -m "feat: naming context formatter for agent-driven cluster naming"`

---

### Task 5: End-to-end validation on HA Core MQTT

Manual verification — not an automated test.

```python
from pathlib import Path
from architecture_model.manifest.recursive import generate_block_manifest
from architecture_model.orchestration.deep_decompose import deep_decompose_block
from architecture_model.orchestration.naming_context import format_naming_context

root = Path("/tmp/ha-core")
block_def = {"name": "Integration MQTT", "dirs": ["homeassistant/components/mqtt"], "files": []}
manifest = generate_block_manifest(root, "F6", block_def)

result = deep_decompose_block(manifest, block_id="F6", block_name="Integration MQTT")
print(f"Sub-components: {len(result.sub_components)}")
for sc in result.sub_components:
    print(f"  {sc.id}: {len(sc.files)} files, {sc.line_count} lines")
    stems = [f.rsplit('/',1)[-1].removesuffix('.py') for f in sc.files[:6]]
    print(f"    Files: {stems}")
    print(f"    Classes: {sc.classes[:5]}")
print(f"\nRelationships: {len(result.internal_relationships)}")
print("\n" + format_naming_context(result))
```

Expected: 3-6 clusters grouping MQTT modules by function (client/transport, discovery, entity platforms, config, etc.)

---

## Dependency Order

Task 1 → Task 2 → Task 3 → Task 4 → Task 5

## Summary

| File | Action | Purpose |
|------|--------|---------|
| `src/architecture_model/core/cluster.py` | Create | Import-graph clustering with target_k |
| `src/architecture_model/orchestration/deep_decompose.py` | Create | Block→sub-components decomposition |
| `src/architecture_model/orchestration/pipeline.py` | Modify | Add `deep=True` option |
| `src/architecture_model/orchestration/naming_context.py` | Create | Compact context for agent naming |
| `tests/test_cluster.py` | Create | Clustering tests |
| `tests/test_deep_decompose.py` | Create | Decomposition tests |
| `tests/test_naming_context.py` | Create | Formatter tests |
| `tests/test_pipeline.py` | Modify | Deep pipeline test |
