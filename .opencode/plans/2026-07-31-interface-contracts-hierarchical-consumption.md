# Interface Contracts + Hierarchical Consumption + Language-Agnostic Protocol

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** (1) Fix the dominant `cross_dep` regeneration failure mode via interface contracts, (2) make hierarchical manifests feed into generation context, and (3) generalize the hierarchical strategy to work with any language/tool via a protocol layer.

**Architecture:**
- **Protocol layer:** Define `SourceUnit` + `DependencyEdge` as the minimal language-agnostic types. The hierarchical pipeline (grouping, fblocks, representativeness) operates on these. Python AST scanner produces them automatically; for other languages, the agent or tools like Madge feed them via `architect_ingest`.
- **Interface contracts:** Auto-extract what each component exposes/requires from source units. Solves cross_dep (80%+ of regen failures).
- **Hierarchical consumption:** Wire per-block manifests into `architect_slice` so focused slicing gives <50x compression (above which pass rate drops below 44%).

**Tech Stack:** Python 3.11+, architecture-model-standard, opencode-arch

**Evidence:**
- cross_dep = 80%+ of regen failures (Celery 181/210, Pydantic 40/40, SQLAlchemy 75/80)
- Compression >50x → 44% pass; <10x → 69% pass
- Components with 10-29 contracts → 70% pass (sweet spot)
- Per-block manifest.json written but never read by any tool
- Current pipeline hardcoded to Python AST; won't work for JS/Go/Rust repos

---

## Part A: Protocol Layer (Language-Agnostic Foundation)

### Task 1: Define SourceUnit and DependencyEdge types

**Files:**
- Create: `architecture-model-standard/src/architecture_model/manifest/protocol.py`
- Test: `architecture-model-standard/tests/test_protocol.py`

**Design:**

```python
# src/architecture_model/manifest/protocol.py
"""Language-agnostic source analysis protocol.

These types represent the MINIMUM data needed for hierarchical decomposition.
They can be populated by:
- Python AST scanner (automatic)
- External tools (Madge for JS, go-callvis for Go)
- Agent reading code (any language)
- JSON ingestion via architect_ingest MCP tool
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExportedSymbol:
    """A symbol exported by a source file."""
    name: str
    kind: str = "function"  # function | class | constant | type | interface
    signature: str = ""     # e.g. "(config: Config) -> Result"
    doc: str = ""           # first line of docstring


@dataclass
class SourceUnit:
    """Language-agnostic representation of a source file.
    
    This is the minimal unit for hierarchical decomposition.
    Replaces ModuleInfo for the grouping/representativeness pipeline.
    """
    file: str                              # relative path from repo root
    has_content: bool = True               # False = trivial (re-export, empty, generated)
    exports: list[ExportedSymbol] = field(default_factory=list)
    language: str = ""                     # python | typescript | go | rust | java | ""

    @property
    def export_names(self) -> list[str]:
        return [e.name for e in self.exports]


@dataclass
class DependencyEdge:
    """A directed dependency between two source files.
    
    source imports symbols from target.
    """
    source: str                            # source file path
    target: str                            # target file path  
    symbols: list[str] = field(default_factory=list)  # which symbols are imported


@dataclass
class SourceGraph:
    """Complete source-level understanding of a repository.
    
    This is the language-agnostic equivalent of Manifest.
    Can be produced by any scanner or by the agent directly.
    """
    units: list[SourceUnit]
    edges: list[DependencyEdge]
    root: str = ""                         # repository root path
    language: str = ""                     # primary language

    @classmethod
    def from_json(cls, data: dict) -> "SourceGraph":
        """Parse from JSON (agent or tool output)."""
        units = [
            SourceUnit(
                file=u["file"],
                has_content=u.get("has_content", True),
                exports=[
                    ExportedSymbol(
                        name=e["name"] if isinstance(e, dict) else e,
                        kind=e.get("kind", "function") if isinstance(e, dict) else "function",
                        signature=e.get("signature", "") if isinstance(e, dict) else "",
                    )
                    for e in u.get("exports", [])
                ],
                language=u.get("language", ""),
            )
            for u in data.get("units", data.get("files", []))
        ]
        edges = [
            DependencyEdge(
                source=e["source"] if isinstance(e, dict) else e[0],
                target=e["target"] if isinstance(e, dict) else e[1],
                symbols=e.get("symbols", []) if isinstance(e, dict) else [],
            )
            for e in data.get("edges", data.get("dependencies", []))
        ]
        return cls(units=units, edges=edges, root=data.get("root", ""), language=data.get("language", ""))

    @classmethod
    def from_manifest(cls, manifest: "Manifest") -> "SourceGraph":
        """Convert a Python Manifest to a SourceGraph."""
        units = []
        for m in manifest.modules:
            exports = []
            for f in m.functions:
                if not f.name.startswith("_"):
                    exports.append(ExportedSymbol(
                        name=f.name, kind="function",
                        signature=f.signature or "",
                        doc=(f.docstring or "").split("\n")[0] if f.docstring else "",
                    ))
            for c in m.classes:
                if not c.name.startswith("_"):
                    exports.append(ExportedSymbol(
                        name=c.name, kind="class",
                        signature="",  # could extract __init__
                    ))
            units.append(SourceUnit(
                file=m.file,
                has_content=bool(m.functions or m.classes),
                exports=exports,
                language="python",
            ))
        edges = [
            DependencyEdge(source=e.source, target=e.target, symbols=[])
            for e in manifest.interfaces
        ]
        return cls(units=units, edges=edges, language="python")

    def to_json(self) -> dict:
        """Serialize to JSON for persistence or transport."""
        return {
            "root": self.root,
            "language": self.language,
            "units": [
                {
                    "file": u.file,
                    "has_content": u.has_content,
                    "exports": [
                        {"name": e.name, "kind": e.kind, "signature": e.signature}
                        for e in u.exports
                    ],
                }
                for u in self.units
            ],
            "edges": [
                {"source": e.source, "target": e.target, "symbols": e.symbols}
                for e in self.edges
            ],
        }
```

**Tests:**

```python
# tests/test_protocol.py
from architecture_model.manifest.protocol import SourceUnit, DependencyEdge, SourceGraph, ExportedSymbol

class TestSourceGraph:
    def test_from_json_minimal(self):
        data = {
            "files": [
                {"file": "src/main.ts", "exports": ["run", "start"]},
                {"file": "src/utils.ts", "exports": [{"name": "format", "kind": "function", "signature": "(s: string) => string"}]},
            ],
            "dependencies": [
                {"source": "src/main.ts", "target": "src/utils.ts", "symbols": ["format"]}
            ]
        }
        graph = SourceGraph.from_json(data)
        assert len(graph.units) == 2
        assert len(graph.edges) == 1
        assert graph.units[0].export_names == ["run", "start"]

    def test_from_manifest(self):
        """Converts Python Manifest to SourceGraph."""
        # ... create a Manifest, verify conversion preserves structure

    def test_roundtrip_json(self):
        graph = SourceGraph(
            units=[SourceUnit(file="a.py", exports=[ExportedSymbol(name="x")])],
            edges=[DependencyEdge(source="a.py", target="b.py")],
        )
        data = graph.to_json()
        restored = SourceGraph.from_json(data)
        assert restored.units[0].file == "a.py"
        assert restored.edges[0].source == "a.py"
```

**Step 5: Commit**

```bash
git commit -m "feat: SourceGraph protocol layer for language-agnostic hierarchical decomposition"
```

---

### Task 2: Adapt grouping to accept SourceGraph

**Files:**
- Modify: `architecture-model-standard/src/architecture_model/manifest/grouping.py`
- Test: `architecture-model-standard/tests/test_grouping_protocol.py`

**Design:** Add a `group_source_graph()` function that operates on `SourceGraph` instead of `list[ModuleInfo] + list[InterfaceEdge]`. The existing `group_modules()` stays for backward compat and internally converts.

```python
def group_source_graph(
    graph: SourceGraph,
    *,
    target_groups: int | None = None,
) -> list[ModuleGroup]:
    """Group source units into logical components using multi-signal affinity.
    
    Language-agnostic version of group_modules().
    Uses subdirectory structure + dependency edges for affinity.
    """
    # Filter trivial units
    kept = [u for u in graph.units if u.has_content]
    if not kept:
        return []

    # Subdirectory grouping (same algorithm as group_modules)
    dir_groups: dict[str, list[str]] = defaultdict(list)
    for u in kept:
        parent = str(PurePosixPath(u.file).parent)
        dir_groups[parent].append(u.file)

    # Edge-based affinity (same algorithm)
    edge_set = {(e.source, e.target) for e in graph.edges}
    # ... same merge logic using edges for affinity scoring
```

The key insight: `group_modules()` already primarily uses `.file` and import edges. The conversion is mechanical.

**Tests:**

```python
class TestGroupSourceGraph:
    def test_groups_by_subdirectory(self):
        graph = SourceGraph(units=[
            SourceUnit(file="src/api/routes.ts"),
            SourceUnit(file="src/api/middleware.ts"),
            SourceUnit(file="src/core/engine.ts"),
            SourceUnit(file="src/core/config.ts"),
        ], edges=[])
        groups = group_source_graph(graph)
        assert len(groups) == 2  # api + core

    def test_edge_affinity_merges_small_groups(self):
        graph = SourceGraph(units=[
            SourceUnit(file="src/a.ts"),
            SourceUnit(file="src/b.ts"),
            SourceUnit(file="lib/c.ts"),
        ], edges=[
            DependencyEdge(source="src/a.ts", target="lib/c.ts"),
        ])
        groups = group_source_graph(graph)
        # b.ts should merge with a.ts (same dir), c.ts separate
```

---

### Task 3: `architect_ingest` MCP tool

**Files:**
- Create: `opencode-arch/src/opencode_arch/mcp/tools/ingest.py`
- Modify: `opencode-arch/src/opencode_arch/mcp/server.py` (register tool)
- Test: `opencode-arch/tests/test_ingest.py`

**Design:** The agent calls `architect_ingest` with a JSON payload describing the source graph. The tool validates, stores it as `.architecture/source-graph.json`, and returns group suggestions.

```python
async def ingest_source_graph(repo_path: str, source_graph_json: str) -> dict:
    """Ingest a language-agnostic source graph for hierarchical decomposition.
    
    The agent (or external tool like Madge) produces this data by analyzing
    the repository's source files and dependencies.
    
    Args:
        repo_path: Repository root path.
        source_graph_json: JSON string with format:
            {
                "language": "typescript",
                "files": [
                    {"file": "src/main.ts", "exports": ["run", "start"], "has_content": true},
                    ...
                ],
                "dependencies": [
                    {"source": "src/main.ts", "target": "src/utils.ts", "symbols": ["format"]},
                    ...
                ]
            }
    
    Returns:
        {
            "units": 25,
            "edges": 40,
            "suggested_groups": [...],
            "suggested_fblocks": {...},
            "stored": ".architecture/source-graph.json"
        }
    """
    import json
    from pathlib import Path
    from architecture_model.manifest.protocol import SourceGraph
    from architecture_model.manifest.grouping import group_source_graph, auto_fblocks

    path = Path(repo_path)
    data = json.loads(source_graph_json)
    graph = SourceGraph.from_json(data)

    # Group and generate F-blocks
    groups = group_source_graph(graph)
    fblocks = auto_fblocks(groups)

    # Persist
    arch_dir = path / ".architecture"
    arch_dir.mkdir(exist_ok=True)
    (arch_dir / "source-graph.json").write_text(json.dumps(graph.to_json(), indent=2))

    return {
        "units": len(graph.units),
        "edges": len(graph.edges),
        "suggested_groups": [{"name": g.name, "files": g.modules} for g in groups],
        "suggested_fblocks": fblocks,
        "stored": ".architecture/source-graph.json",
    }
```

**Agent workflow example (TypeScript repo with Madge):**

```
Agent: "Let me analyze this TypeScript project's dependencies"
Agent: [runs] npx madge --json src/ > /tmp/deps.json
Agent: [reads] /tmp/deps.json → converts to source_graph_json format
Agent: [calls] architect_ingest(repo_path, source_graph_json)
→ Gets back: suggested_groups, fblocks
Agent: Uses this to build architecture model
```

**Agent workflow example (Go repo, no tools):**

```
Agent: [reads] go.mod, finds module path
Agent: [lists] find . -name "*.go" | grep -v vendor
Agent: [reads first 30 lines of each file] → extracts exports (capitalized) + imports
Agent: [builds JSON] {files: [...], dependencies: [...]}
Agent: [calls] architect_ingest(repo_path, source_graph_json)
→ Gets back: suggested_groups, fblocks
```

---

## Part B: Interface Contracts (Fix cross_dep)

### Task 4: Define ComponentInterface type

**Files:**
- Modify: `architecture-model-standard/src/architecture_model/core/types.py`
- Test: `architecture-model-standard/tests/test_interface_contracts.py`

```python
@dataclass
class ComponentInterface:
    """What a component exposes to and requires from other components.
    
    This is the key data for cross-component regeneration.
    Without it, the agent can't generate proper imports/exports.
    """
    exposes: list[ExportedSymbol] = field(default_factory=list)  # reuses protocol type
    requires: list[str] = field(default_factory=list)  # "COMP-ID.symbol_name"
```

Add to `Component`:
```python
    interface: Optional[ComponentInterface] = None
```

---

### Task 5: Extract interfaces from SourceGraph

**Files:**
- Modify: `architecture-model-standard/src/architecture_model/orchestration/auto_enrich.py`
- Test: `architecture-model-standard/tests/test_interface_contracts.py`

```python
def extract_component_interfaces(
    model: ArchitectureModel,
    graph: SourceGraph,
) -> None:
    """Extract interface contracts for each component from source graph.
    
    For each component:
    - exposes: public symbols from its files
    - requires: symbols imported from other components' files
    
    Works with any language — only needs SourceGraph (not Python Manifest).
    """
    # Build file→component mapping
    file_to_comp = {}
    for comp in model.entities.components:
        for f in (comp.files or []):
            file_to_comp[f] = comp.id

    # Build file→unit mapping
    unit_by_file = {u.file: u for u in graph.units}

    for comp in model.entities.components:
        exposes = []
        requires = []

        # Collect exports from component's files
        for f in (comp.files or []):
            unit = unit_by_file.get(f)
            if not unit:
                continue
            exposes.extend(unit.exports)

        # Collect requires from edges INTO this component from other components
        comp_files = set(comp.files or [])
        for edge in graph.edges:
            if edge.source in comp_files and edge.target not in comp_files:
                target_comp_id = file_to_comp.get(edge.target)
                if target_comp_id:
                    for sym in edge.symbols:
                        requires.append(f"{target_comp_id}.{sym}")
                    if not edge.symbols:
                        # Edge exists but symbols unknown — mark generic dependency
                        requires.append(f"{target_comp_id}.*")

        comp.interface = ComponentInterface(exposes=exposes, requires=requires)
```

---

### Task 6: Wire into pipeline + update confidence

Same as original plan Tasks 3-4: call `extract_component_interfaces` in `enrich_from_manifest`, add confidence boost for interface.

---

## Part C: Hierarchical Context Consumption

### Task 7: Focused slice uses SourceGraph for rich context

**Files:**
- Modify: `opencode-arch/src/opencode_arch/mcp/tools/slice.py`
- Create: `opencode-arch/src/opencode_arch/context/block_formatter.py`

When `focus="F1"`:
1. Load source graph (from `.architecture/source-graph.json` or generate from manifest)
2. Filter to the F-block's files
3. Format rich context: interface + all exported symbols + dependency summary
4. This gives <50x compression per block (vs >200x for full repo)

```python
def format_block_context(
    component: Component,
    graph: SourceGraph,
    block_files: set[str],
    budget: int = 4000,
) -> str:
    """Format rich per-block context from source graph.
    
    Priority order (progressive truncation):
    1. Interface (what this block exposes/requires) — always included
    2. Exported symbol signatures — included if budget allows
    3. Dependency graph within block — included if budget allows
    4. Docstrings — included at full detail level
    """
    ...
```

### Task 8: Cache source graph + block manifests

Load from `.architecture/source-graph.json` instead of regenerating. Only regenerate if file doesn't exist or is older than source files.

### Task 9: Integration test on Celery + TypeScript mock

Two tests:
1. Celery (Python, uses generate_manifest → SourceGraph.from_manifest)
2. Mock TypeScript repo (agent-produced JSON → architect_ingest → full pipeline)

Both should achieve >60% confidence and demonstrate <50x per-block compression.

---

## Data Flow (Generalized)

```
┌─────────────────────────────────────────────────────────┐
│                     INPUT SOURCES                         │
├──────────────┬──────────────┬───────────────────────────┤
│ Python AST   │ Madge (JS)   │ Agent reading code        │
│ scan_file()  │ npx madge    │ (any language)            │
│ ↓            │ ↓            │ ↓                         │
│ Manifest     │ JSON deps    │ JSON files + deps         │
└──────┬───────┴──────┬───────┴──────────┬────────────────┘
       │              │                  │
       ▼              ▼                  ▼
   from_manifest()  from_json()      from_json()
       │              │                  │
       └──────────────┼──────────────────┘
                      ▼
              ┌──────────────┐
              │ SourceGraph  │  ← THE PROTOCOL LAYER
              │ units + edges│
              └──────┬───────┘
                     │
        ┌────────────┼────────────────┐
        ▼            ▼                ▼
  group_source   auto_fblocks   extract_interfaces
  _graph()       ()              ()
        │            │                │
        ▼            ▼                ▼
  ModuleGroup[]  F-block dict   ComponentInterface
        │            │                │
        └────────────┼────────────────┘
                     ▼
           ┌─────────────────┐
           │ ArchitectureModel│
           │ + enriched comps │
           └────────┬────────┘
                    │
        ┌───────────┼────────────┐
        ▼           ▼            ▼
  architect_   architect_   architect_
  slice        check       generate
  (focused)    (hierarchical) (per-block)
```

---

## Execution Order

**Phase 1: Protocol layer (architecture-model-standard)**
- Task 1: SourceUnit, DependencyEdge, SourceGraph types + from_json/from_manifest
- Task 2: group_source_graph() + adapt auto_fblocks

**Phase 2: Interface contracts (architecture-model-standard)**  
- Task 4: ComponentInterface type
- Task 5: extract_component_interfaces(model, graph)
- Task 6: Wire into pipeline + confidence scoring

**Phase 3: Consumption layer (opencode-arch)**
- Task 3: architect_ingest MCP tool
- Task 7: Focused slice uses SourceGraph
- Task 8: Caching

**Phase 4: Validation**
- Task 9: E2E tests (Python + non-Python)

---

## Expected Outcomes

| Metric | Before | After | Mechanism |
|--------|--------|-------|-----------|
| Language support | Python only | Any | SourceGraph protocol |
| Component confidence | 0.30-0.55 | **>0.60** | Interface adds +0.10-0.15 |
| cross_dep failures | 80%+ | **<30%** | Interface contracts provide stubs |
| Per-block compression | >200x | **<50x** | Block-focused slicing with SourceGraph |
| Blind mode pass rate | 48% | **>65%** | Less compression + interface stubs |
| Agent workflow for non-Python | Not possible | Documented + tooled | architect_ingest + from_json |
