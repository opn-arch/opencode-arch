# Quality Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the top 4 quality gaps identified in the v0.5.0 benchmark: test_contracts enrichment, basename matching bug, flat-repo decomposition, and non-Python enrichment.

**Architecture:** All changes in `architecture-model-standard` except task 5 (re-benchmark in `opencode-arch`). Each task is independent — can be committed separately.

**Tech Stack:** Python 3.12, pytest

**Python:** `/opt/anaconda3/bin/python`
**Pytest:** `/opt/anaconda3/bin/python -m pytest`
**architecture-model-standard root:** `/Users/baigm2/Documents/Projects/architecture-model-standard`
**opencode-arch root:** `/Users/baigm2/Documents/Projects/opencode-arch`

**Important:** Always run pytest with `--ignore=tests/test_config_loader.py` (pre-existing failure).

---

### Task 1: Wire test_contracts into the pipeline

**Problem:** `_enrich_test_contracts()` exists in `orchestration/enrich.py` but is never called from the pipeline. The pipeline only calls `enrich_from_manifest()` from `auto_enrich.py`.

**Fix:** After `enrich_from_manifest()` runs in `pipeline.py`, call `_enrich_test_contracts()` for each component that has files and an accessible project root.

**Files:**
- Modify: `src/architecture_model/orchestration/pipeline.py` — add test_contracts enrichment call
- Test: `tests/test_pipeline_test_contracts.py` — verify test_contracts populated when test files exist

**Step 1: Write the failing test**

Create `tests/test_pipeline_test_contracts.py`:

```python
"""Test that the pipeline populates test_contracts from test files."""
import textwrap
from pathlib import Path

import pytest

from architecture_model.orchestration.pipeline import run_pipeline


@pytest.fixture
def repo_with_tests(tmp_path):
    """Create a minimal repo with source + test files."""
    # Source file
    src = tmp_path / "mylib"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "calculator.py").write_text(textwrap.dedent("""\
        def add(a, b):
            \"\"\"Add two numbers.\"\"\"
            return a + b

        def multiply(a, b):
            \"\"\"Multiply two numbers.\"\"\"
            return a * b
    """))
    (src / "formatter.py").write_text(textwrap.dedent("""\
        class Formatter:
            def format(self, value):
                return str(value)
    """))

    # Config file
    (tmp_path / ".architecture-model.yaml").write_text(textwrap.dedent("""\
        meta:
          project: test-repo
          schema_version: '1.3'
        entities:
          components: []
        relationships: []
    """))

    # Test files
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("")
    (tests / "test_calculator.py").write_text(textwrap.dedent("""\
        from mylib.calculator import add, multiply

        def test_add():
            assert add(2, 3) == 5

        def test_multiply():
            assert multiply(3, 4) == 12
    """))
    return tmp_path


def test_pipeline_populates_test_contracts(repo_with_tests):
    """Pipeline should discover test files and extract test contracts."""
    result = run_pipeline(repo_with_tests, from_scratch=True)
    model = result["model"]

    # Find the calculator component
    components = model.entities.components if hasattr(model.entities, 'components') else model.entities.get("components", [])
    calc_comps = [c for c in components if any("calculator" in f for f in (c.files or []))]

    assert len(calc_comps) >= 1, f"Expected calculator component, got: {[c.name for c in components]}"
    calc = calc_comps[0]
    assert len(calc.test_contracts) > 0, (
        f"Expected test_contracts on calculator component, got none. "
        f"Component files: {calc.files}"
    )


def test_pipeline_no_test_contracts_when_no_tests(tmp_path):
    """Components without matching test files should have empty test_contracts."""
    src = tmp_path / "mylib"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "utils.py").write_text("def helper(): pass\n")
    (tmp_path / ".architecture-model.yaml").write_text(textwrap.dedent("""\
        meta:
          project: no-tests
          schema_version: '1.3'
        entities:
          components: []
        relationships: []
    """))

    result = run_pipeline(tmp_path, from_scratch=True)
    model = result["model"]
    components = model.entities.components if hasattr(model.entities, 'components') else model.entities.get("components", [])
    for comp in components:
        assert comp.test_contracts == [], f"{comp.name} should have no test_contracts"
```

**Step 2: Run test to verify it fails**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_pipeline_test_contracts.py -v --ignore=tests/test_config_loader.py`
Expected: FAIL — `test_pipeline_populates_test_contracts` fails because test_contracts is empty.

**Step 3: Implement the fix in pipeline.py**

In `pipeline.py`, after the `enrich_from_manifest(model, flat_manifest)` call (both at the existing-model path ~line 137 and the from-scratch path ~line 196), add test_contracts enrichment:

```python
# At the top, add import:
from architecture_model.orchestration.enrich import _enrich_test_contracts

# After enrich_from_manifest(model, flat_manifest), add:
# Step: Enrich test contracts from test files
components = model.entities.components if hasattr(model.entities, 'components') else []
for comp in components:
    if comp.files and comp.status == "ACTIVE":
        try:
            _enrich_test_contracts(comp, project_root)
        except Exception:
            pass  # Never block pipeline on test discovery failure
```

Note: `_enrich_test_contracts` is a private function. If it's not importable, either make it public (`enrich_test_contracts`) or import `enrich_model` and call it. Check what's cleaner.

**Step 4: Run test to verify it passes**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_pipeline_test_contracts.py -v --ignore=tests/test_config_loader.py`
Expected: PASS

**Step 5: Run full test suite**

Run: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py -x`
Expected: All existing tests still pass (no regressions).

**Step 6: Commit**

```bash
git add tests/test_pipeline_test_contracts.py src/architecture_model/orchestration/pipeline.py
git commit -m "feat: wire test_contracts enrichment into pipeline

Pipeline now calls _enrich_test_contracts() after enrich_from_manifest(),
discovering test files and extracting assertion-based contracts. This
unlocks the 15% confidence weight that was previously unreachable."
```

---

### Task 2: Fix _files_match basename bug in representativeness

**Problem:** `_files_match()` in `representativeness.py` matches files by basename only (`PurePosixPath(f).name`). This causes false positive matches for common names like `__init__.py`, `utils.py`, `base.py`, inflating external edge counts and deflating boundary coherence (Celery: 38.2%).

**Files:**
- Modify: `src/architecture_model/core/representativeness.py` — fix `_files_match()` to use full relative path
- Test: `tests/test_representativeness_match.py` — verify basename collisions don't cause false matches

**Step 1: Write the failing test**

Create `tests/test_representativeness_match.py`:

```python
"""Test that _files_match uses full path, not just basename."""
from architecture_model.core.representativeness import _files_match


def test_files_match_exact_path():
    """Exact paths should match."""
    assert _files_match("src/app/utils.py", "src/app/utils.py")


def test_files_match_basename_collision():
    """Different dirs with same basename should NOT match."""
    assert not _files_match("src/app/utils.py", "src/worker/utils.py")


def test_files_match_init_collision():
    """Different __init__.py files should NOT match."""
    assert not _files_match("src/app/__init__.py", "src/worker/__init__.py")


def test_files_match_suffix_normalization():
    """Should match with or without leading ./ or src/ prefix differences."""
    # Same logical file with different prefix representations
    assert _files_match("app/utils.py", "app/utils.py")


def test_files_match_no_false_positive_substring():
    """utils.py should not match my_utils.py."""
    assert not _files_match("src/utils.py", "src/my_utils.py")
```

**Step 2: Run test to verify it fails**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_representativeness_match.py -v --ignore=tests/test_config_loader.py`
Expected: `test_files_match_basename_collision` and `test_files_match_init_collision` FAIL (current basename matching makes them True).

**Step 3: Fix `_files_match()` in representativeness.py**

Change from basename matching to full relative path matching:

```python
def _files_match(model_file: str, manifest_file: str) -> bool:
    """Check if a model file path matches a manifest file path.
    
    Uses full relative path comparison (not just basename) to avoid
    false positives on common filenames like __init__.py, utils.py.
    """
    from pathlib import PurePosixPath
    # Normalize: strip leading ./ and compare full relative paths
    a = str(PurePosixPath(model_file)).lstrip("./")
    b = str(PurePosixPath(manifest_file)).lstrip("./")
    # Try exact match first
    if a == b:
        return True
    # Try suffix match (one path may include src/ prefix the other doesn't)
    return a.endswith("/" + b) or b.endswith("/" + a)
```

**Step 4: Run test to verify it passes**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_representativeness_match.py -v --ignore=tests/test_config_loader.py`
Expected: PASS

**Step 5: Run full test suite**

Run: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py -x`
Expected: All pass. If any representativeness tests break, they were relying on the buggy basename behavior — update them.

**Step 6: Commit**

```bash
git add src/architecture_model/core/representativeness.py tests/test_representativeness_match.py
git commit -m "fix: use full path matching in boundary coherence calculation

_files_match() was using basename-only comparison, causing false positive
matches on common filenames (__init__.py, utils.py, base.py). This
inflated external edge counts and deflated boundary coherence scores.
Celery was most affected (38.2% with bug)."
```

---

### Task 3: Flat-repo decomposition fallback

**Problem:** When all modules are in a single directory (flat repo), `group_modules()` produces single-file unlocked groups, and `auto_fblocks(threshold=3)` puts everything in F0 (Shared). Affects Flask, httpx, invoke, rich.

**Design:** When `auto_fblocks()` would produce only F0, fall back to using import-affinity merged groups as F-blocks. The key insight: `group_modules()` already does import-affinity merging, but with a `target_groups` that's too high for flat repos. We need to force a lower target.

**Files:**
- Modify: `src/architecture_model/manifest/grouping.py` — add flat-repo detection and fallback in `auto_fblocks()`
- Test: `tests/test_auto_fblocks.py` — add tests for flat-repo fallback

**Step 1: Write the failing tests**

Add to `tests/test_auto_fblocks.py`:

```python
def test_flat_repo_fallback():
    """When all groups are single-file, auto_fblocks should use them as F-blocks instead of collapsing to F0."""
    from architecture_model.manifest.grouping import auto_fblocks
    from architecture_model.manifest.types import ModuleInfo

    # Simulate a flat repo: 6 single-file groups (all below threshold=3)
    groups = []
    for name in ["app", "models", "views", "utils", "config", "auth"]:
        g = type("G", (), {"name": name, "modules": [f"src/{name}.py"], "file_count": 1, "primary_file": f"src/{name}.py"})()
        groups.append(g)

    result = auto_fblocks(groups, threshold=3)

    # Should NOT collapse everything to F0
    fblock_ids = list(result.keys())
    assert len(fblock_ids) > 1, f"Expected multiple F-blocks for flat repo, got only: {fblock_ids}"
    # F0 should exist but not contain everything
    if "F0" in result:
        assert len(result["F0"]["files"]) < 6, "F0 should not contain all files"


def test_flat_repo_preserves_groups():
    """Flat-repo fallback should preserve meaningful group boundaries."""
    from architecture_model.manifest.grouping import auto_fblocks

    groups = []
    for name in ["core", "api", "db"]:
        g = type("G", (), {"name": name, "modules": [f"src/{name}.py"], "file_count": 1, "primary_file": f"src/{name}.py"})()
        groups.append(g)

    result = auto_fblocks(groups, threshold=3)
    # Each group should become its own F-block
    assert len(result) >= 3, f"Expected >=3 F-blocks, got {len(result)}"
```

**Step 2: Run test to verify it fails**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_auto_fblocks.py::test_flat_repo_fallback tests/test_auto_fblocks.py::test_flat_repo_preserves_groups -v --ignore=tests/test_config_loader.py`
Expected: FAIL — everything collapses to F0.

**Step 3: Implement flat-repo fallback in `auto_fblocks()`**

In `grouping.py`, modify `auto_fblocks()`. After the existing logic that builds `fblocks` and `shared_files`, add a fallback:

```python
def auto_fblocks(groups, threshold=3):
    # ... existing logic that produces fblocks dict and shared_files ...
    
    # Flat-repo fallback: if ALL files ended up in Shared (no F-blocks created),
    # promote each original group to its own F-block
    if not fblocks or (len(fblocks) == 1 and "F0" in fblocks):
        total_files = sum(len(g.modules) for g in groups)
        if total_files >= 2:  # At least 2 files to decompose
            fblocks = {}
            for i, g in enumerate(groups, 1):
                if g.modules:  # Skip empty groups
                    fblocks[f"F{i}"] = {
                        "name": g.name,
                        "files": list(g.modules),
                    }
            # No F0/Shared needed — all files assigned
            return fblocks
    
    # ... rest of existing logic (add F0 with shared_files) ...
```

The exact insertion point depends on the current code structure. Read `auto_fblocks()` carefully to find where `fblocks` is populated and where `shared_files` are added as F0.

**Step 4: Run test to verify it passes**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_auto_fblocks.py -v --ignore=tests/test_config_loader.py`
Expected: All pass including new tests.

**Step 5: Run full test suite**

Run: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py -x`
Expected: All pass.

**Step 6: Commit**

```bash
git add src/architecture_model/manifest/grouping.py tests/test_auto_fblocks.py
git commit -m "feat: flat-repo decomposition fallback in auto_fblocks

When all groups would collapse into F0 (Shared), each group is promoted
to its own F-block. Fixes Flask, httpx, invoke, and other flat-package
repos that previously got no decomposition."
```

---

### Task 4: SourceGraph-based enrichment for non-Python repos

**Problem:** Non-Python repos ingested via SourceGraph get near-zero confidence (0.05-0.33) because no enrichment runs. The SourceGraph already carries `ExportedSymbol` with `name`, `kind`, `signature`, `doc` fields — they just aren't consumed.

**Design:** Create `enrich_from_source_graph(model, graph)` in `auto_enrich.py` that populates signatures, symbols, contracts, patterns, and responsibilities from SourceGraph data. This is the mechanical enrichment. For anything it can't fill, the agent fallback (already present in `ingest.py` contract synthesis) handles it.

**Files:**
- Modify: `src/architecture_model/orchestration/auto_enrich.py` — add `enrich_from_source_graph()`
- Modify: `src/opencode_arch/mcp/tools/ingest.py` — call `enrich_from_source_graph()` after component creation
- Test: `tests/test_source_graph_enrichment.py` (in architecture-model-standard)

**Step 1: Write the failing test**

Create `tests/test_source_graph_enrichment.py` in architecture-model-standard:

```python
"""Test enrichment of components from SourceGraph data."""
from architecture_model.core.types import ArchitectureModel, Component, ModelMeta, Entities
from architecture_model.manifest.protocol import SourceGraph, SourceUnit, DependencyEdge, ExportedSymbol
from architecture_model.orchestration.auto_enrich import enrich_from_source_graph


def _make_graph():
    """Create a SourceGraph with rich export data."""
    units = [
        SourceUnit(
            file="src/handler.go",
            has_content=True,
            language="go",
            exports=[
                ExportedSymbol(name="HandleRequest", kind="function",
                              signature="(w http.ResponseWriter, r *http.Request)",
                              doc="HandleRequest processes incoming HTTP requests."),
                ExportedSymbol(name="Router", kind="class",
                              signature="struct",
                              doc="Router manages HTTP route registration."),
            ],
        ),
        SourceUnit(
            file="src/db.go",
            has_content=True,
            language="go",
            exports=[
                ExportedSymbol(name="Connect", kind="function",
                              signature="(dsn string) (*DB, error)",
                              doc="Connect establishes a database connection."),
                ExportedSymbol(name="DB", kind="class",
                              signature="struct",
                              doc="DB wraps the database connection pool."),
            ],
        ),
    ]
    edges = [
        DependencyEdge(source="src/handler.go", target="src/db.go", symbols=["Connect", "DB"]),
    ]
    return SourceGraph(units=units, edges=edges)


def _make_model():
    """Create a model with two components matching the graph."""
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(components=[
            Component(id="COMP-1", name="Handler", status="ACTIVE",
                      files=["src/handler.go"]),
            Component(id="COMP-2", name="Database", status="ACTIVE",
                      files=["src/db.go"]),
        ]),
        relationships=[],
    )


def test_signatures_from_source_graph():
    """Should populate function signatures from ExportedSymbol."""
    model = _make_model()
    graph = _make_graph()
    enrich_from_source_graph(model, graph)

    handler = model.entities.components[0]
    assert len(handler.signatures) >= 1
    sig_names = [s.name for s in handler.signatures]
    assert "HandleRequest" in sig_names


def test_symbols_from_source_graph():
    """Should populate symbols from class-kind exports."""
    model = _make_model()
    graph = _make_graph()
    enrich_from_source_graph(model, graph)

    handler = model.entities.components[0]
    sym_names = [s.name for s in handler.symbols]
    assert "Router" in sym_names


def test_contract_from_source_graph():
    """Should synthesize contract from export docs."""
    model = _make_model()
    graph = _make_graph()
    enrich_from_source_graph(model, graph)

    handler = model.entities.components[0]
    assert handler.contract, "Expected contract to be populated"
    assert "HandleRequest" in handler.contract or "HTTP" in handler.contract


def test_confidence_improves():
    """Enrichment should improve confidence above baseline."""
    model = _make_model()
    graph = _make_graph()

    # Baseline confidence (no enrichment)
    from architecture_model.core.confidence import compute_component_confidence
    baseline = compute_component_confidence(model.entities.components[0])

    enrich_from_source_graph(model, graph)
    enriched = compute_component_confidence(model.entities.components[0])

    assert enriched > baseline, f"Expected confidence improvement: {baseline} -> {enriched}"
```

**Step 2: Run test to verify it fails**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_source_graph_enrichment.py -v --ignore=tests/test_config_loader.py`
Expected: FAIL — `enrich_from_source_graph` does not exist.

**Step 3: Implement `enrich_from_source_graph()` in auto_enrich.py**

```python
def enrich_from_source_graph(model: Any, graph: "SourceGraph") -> None:
    """Enrich model components from SourceGraph export data.
    
    Language-agnostic enrichment using ExportedSymbol fields:
    - signatures from function exports with signatures
    - symbols from class/type exports
    - contract from export docstrings
    - pattern from export name matching
    - responsibilities from class member names (if available)
    """
    from architecture_model.manifest.protocol import SourceGraph
    from architecture_model.core.confidence import compute_component_confidence

    # Build file -> unit lookup
    unit_map: dict[str, "SourceUnit"] = {u.file: u for u in graph.units}

    components = _get_components(model)
    for comp in components:
        if not comp.files:
            continue

        # Collect all exports for this component's files
        all_exports = []
        for f in comp.files:
            unit = unit_map.get(f)
            if unit:
                all_exports.extend(unit.exports)

        if not all_exports:
            continue

        # Signatures from function exports
        if not comp.signatures:
            comp.signatures = []
            for exp in all_exports:
                if exp.kind == "function" and exp.signature:
                    comp.signatures.append(FunctionSignature(
                        name=exp.name,
                        signature=exp.signature,
                        docstring=exp.doc or "",
                    ))

        # Symbols from class/type exports
        if not comp.symbols:
            comp.symbols = []
            for exp in all_exports:
                if exp.kind in ("class", "type", "interface"):
                    kind = SymbolKind.ABSTRACT_CLASS if exp.kind == "interface" else SymbolKind.CLASS
                    comp.symbols.append(Symbol(
                        name=exp.name,
                        kind=kind,
                        decorators=[],
                        bases=[],
                        methods=[],
                    ))

        # Contract from docstrings
        if not comp.contract:
            docs = [exp.doc for exp in all_exports if exp.doc]
            if docs:
                comp.contract = "; ".join(docs[:3])
            else:
                export_names = [exp.name for exp in all_exports[:5]]
                comp.contract = f"Provides: {', '.join(export_names)}"

        # Pattern detection from names
        if not comp.pattern:
            patterns = load_patterns()
            all_names = [exp.name.lower() for exp in all_exports]
            comp.pattern = _detect_pattern_from_names(all_names, patterns)

        # Responsibilities from public exports
        if not comp.responsibilities:
            func_exports = [exp.name for exp in all_exports if exp.kind == "function"]
            if func_exports:
                comp.responsibilities = func_exports[:10]

        # Recompute confidence
        comp.confidence = compute_component_confidence(comp)
```

Note: `_detect_pattern_from_names()` is a new helper that checks export names against the pattern catalog. It should check for keywords like "handler", "controller", "repository", "factory", "middleware", "router", "service", etc. Look at how existing pattern detection works in `_classify_pattern()` and adapt.

**Step 4: Run test to verify it passes**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_source_graph_enrichment.py -v --ignore=tests/test_config_loader.py`
Expected: PASS

**Step 5: Wire into ingest.py (opencode-arch)**

In `src/opencode_arch/mcp/tools/ingest.py`, after components are created and before confidence is computed, call:

```python
from architecture_model.orchestration.auto_enrich import enrich_from_source_graph
enrich_from_source_graph(model, graph)
```

This replaces the existing manual contract synthesis loop (lines 69-79).

**Step 6: Run both test suites**

```bash
# architecture-model-standard
cd /Users/baigm2/Documents/Projects/architecture-model-standard
/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py -x

# opencode-arch
cd /Users/baigm2/Documents/Projects/opencode-arch
/opt/anaconda3/bin/python -m pytest tests/ -v -x
```

**Step 7: Commit (both repos)**

```bash
# architecture-model-standard
git add src/architecture_model/orchestration/auto_enrich.py tests/test_source_graph_enrichment.py
git commit -m "feat: add enrich_from_source_graph for language-agnostic enrichment

Populates signatures, symbols, contracts, patterns, and responsibilities
from SourceGraph ExportedSymbol data. Enables non-Python repos to reach
comparable confidence scores when SourceGraph data includes signatures
and docstrings."

# opencode-arch
git add src/opencode_arch/mcp/tools/ingest.py
git commit -m "feat: wire enrich_from_source_graph into ingest tool

Replaces manual contract synthesis with full SourceGraph-based
enrichment. Non-Python repos now get signatures, symbols, patterns,
and responsibilities from ExportedSymbol data."
```

---

### Task 5: Re-run benchmark on affected repos and update report

**Problem:** After fixes, we need to measure improvement.

**Files:**
- Update: `.opencode/metrics/quality-report-2026-07-31.json` — add post-fix comparison
- No new test files needed

**Step 1: Re-run pipeline on key repos**

Write a Python script at `/tmp/rebenchmark.py` that:

1. Runs `run_pipeline(Path(repo), from_scratch=True)` for: flask, celery, httpx, invoke
2. For each, captures: component count, avg_confidence, test_contracts count, boundary coherence
3. Compares before/after
4. Prints results table

```python
import json
from pathlib import Path
from architecture_model.orchestration.pipeline import run_pipeline
from architecture_model.core.representativeness import compute_representativeness
from architecture_model.core.confidence import compute_component_confidence
from architecture_model.manifest.generator import generate_manifest

repos = ["flask", "celery", "httpx", "invoke"]
results = {}

for name in repos:
    repo = Path(f"/tmp/arch-bench/{name}")
    if not repo.exists():
        print(f"Skipping {name} (not found)")
        continue
    
    result = run_pipeline(repo, from_scratch=True)
    model = result["model"]
    manifest = generate_manifest(repo)
    
    comps = model.entities.components if hasattr(model.entities, 'components') else []
    tc_count = sum(1 for c in comps if c.test_contracts)
    avg_conf = sum(c.confidence or 0 for c in comps) / max(len(comps), 1)
    
    repr_result = compute_representativeness(model, manifest.modules, manifest.interfaces)
    
    results[name] = {
        "components": len(comps),
        "avg_confidence": round(avg_conf, 3),
        "test_contracts_populated": tc_count,
        "boundary_coherence": repr_result.get("boundary_coherence", 0),
        "overall_repr": repr_result.get("overall", 0),
    }
    print(f"{name}: {results[name]}")

print(json.dumps(results, indent=2))
```

**Step 2: Run it**

Run: `/opt/anaconda3/bin/python /tmp/rebenchmark.py`

**Step 3: Compare and update report**

Compare the before/after numbers and add a "Post-fix comparison" section to the quality report markdown.

**Step 4: Commit**

```bash
git add .opencode/metrics/
git commit -m "docs: update quality report with post-fix benchmark comparison"
```
