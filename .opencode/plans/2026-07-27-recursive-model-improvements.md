# Recursive Model Improvements Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix manifest non-determinism, make recursive manifests model-aware, clarify the decomposer split, and regenerate missing sub-models — enabling reliable self-modeling and extraction feedback loops.

**Architecture:** Four independent improvements to the architecture-model-standard that collectively make the recursive modeling pipeline deterministic, accurate, and complete. Each task can be committed independently.

**Tech Stack:** Python 3.12, dataclasses, AST scanning, YAML, pytest

**Target repo:** `/Users/baigm2/Documents/Projects/architecture-model-standard`

---

## Task 1: Fix Manifest Non-Determinism

**Files:**
- Modify: `src/architecture_model/manifest/blocks.py:153`
- Create: `tests/test_manifest_determinism.py`

**Step 1: Write the failing test**

```python
"""Tests that manifest generation is deterministic across calls."""
import json
import subprocess
import sys
from pathlib import Path


def test_manifest_deterministic_across_processes(tmp_path):
    """Manifest JSON must be identical across separate Python processes."""
    pkg = tmp_path / "src" / "mymod"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text(
        'def compute(x: int) -> int:\n    """Compute."""\n    return x * 2\n\n'
        'def transform(data: list) -> dict:\n    """Transform."""\n    return {}\n'
    )
    (pkg / "utils.py").write_text(
        'def helper() -> str:\n    return "ok"\n\n'
        'def another() -> str:\n    return "yes"\n'
    )

    script = f"""
import json, sys
sys.path.insert(0, "{Path("src").resolve()}")
from architecture_model.manifest.generator import generate_manifest
from pathlib import Path
m = generate_manifest(Path("{tmp_path}"))
d = m.to_dict()
del d["generated_at"]
print(json.dumps(d, sort_keys=True))
"""

    results = []
    for _ in range(5):
        r = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0, r.stderr
        results.append(r.stdout.strip())

    assert len(set(results)) == 1, f"Got {len(set(results))} distinct outputs"
```

**Step 2: Run test to verify it fails**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_manifest_determinism.py -v`
Expected: FAIL — different outputs due to `list(set(outputs))` ordering

**Step 3: Fix the non-determinism**

In `src/architecture_model/manifest/blocks.py` line 153, change:
```python
# Before:
outputs=list(set(outputs))[:4],

# After:
outputs=sorted(set(outputs))[:4],
```

**Step 4: Run test to verify it passes**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_manifest_determinism.py -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `/opt/anaconda3/bin/python -m pytest tests/ --ignore=tests/test_config_loader.py -q`
Expected: 491+ passed

**Step 6: Commit**

```bash
git add src/architecture_model/manifest/blocks.py tests/test_manifest_determinism.py
git commit -m "fix: sort set outputs in blocks.py for deterministic manifests"
```

---

## Task 2: Set manifest_hash (Staleness Check Works)

**Files:**
- Modify: `.architecture-model.yaml` (meta section)

**Step 1: Verify the coverage staleness fix is in place**

Check that `_check_staleness` in `coverage.py` excludes `generated_at`:
```python
stable_manifest = {k: v for k, v in manifest.items() if k != "generated_at"}
```

**Step 2: Compute and set the manifest hash**

Run:
```python
from architecture_model.manifest.generator import generate_manifest
from pathlib import Path
import hashlib, json

manifest = generate_manifest(Path('.')).to_dict()
stable = {k: v for k, v in manifest.items() if k != 'generated_at'}
h = hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()[:16]
print(h)
```

Set the result in `.architecture-model.yaml` under `meta:`:
```yaml
meta:
  project: architecture-model-standard
  schema_version: '2.0'
  manifest_hash: <computed_hash>
```

**Step 3: Verify coverage shows 100%**

```python
from architecture_model import load_model
from architecture_model.core.coverage import coverage_report
from architecture_model.manifest.generator import generate_manifest
from pathlib import Path

model = load_model('.architecture-model.yaml')
manifest = generate_manifest(Path('.')).to_dict()
result = coverage_report(model, manifest)
for c in result.checks:
    print(f'{c.name}: {c.score}%')
# Expected: all 100%
```

**Step 4: Commit**

```bash
git add .architecture-model.yaml
git commit -m "chore: set manifest_hash for staleness tracking"
```

---

## Task 3: Make Recursive Manifest Model-Aware

**Files:**
- Modify: `src/architecture_model/manifest/recursive.py:29-33`
- Create: `tests/test_recursive_model_aware.py`

**Step 1: Write failing tests**

```python
"""Tests for model-aware recursive manifest generation."""
from architecture_model.core.types import (
    ArchitectureModel, Component, Entities, ModelMeta, Status,
)
from architecture_model.manifest.recursive import _block_id_to_component_id


def _make_model(components):
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="2.0"),
        entities=Entities(components=components),
        relationships=[],
    )


class TestComponentIdResolution:
    def test_resolves_from_model_by_fblock(self):
        model = _make_model([
            Component(id="COMP-MY-PARSER", name="Parser", f_block="F1", status=Status.ACTIVE),
        ])
        class FakeConfig:
            fblock_dict = {"F1": {"name": "Cli"}}
        assert _block_id_to_component_id("F1", FakeConfig(), model) == "COMP-MY-PARSER"

    def test_falls_back_to_convention_without_model(self):
        class FakeConfig:
            fblock_dict = {"F1": {"name": "Cli"}}
        assert _block_id_to_component_id("F1", FakeConfig(), None) == "COMP-CLI"

    def test_falls_back_when_no_match(self):
        model = _make_model([
            Component(id="COMP-OTHER", name="Other", f_block="F99", status=Status.ACTIVE),
        ])
        class FakeConfig:
            fblock_dict = {"F1": {"name": "Cli"}}
        assert _block_id_to_component_id("F1", FakeConfig(), model) == "COMP-CLI"

    def test_multiple_components_returns_first(self):
        model = _make_model([
            Component(id="COMP-CORE", name="Core", f_block="F3", status=Status.ACTIVE),
            Component(id="COMP-VIZ", name="Viz", f_block="F3", status=Status.ACTIVE),
        ])
        class FakeConfig:
            fblock_dict = {"F3": {"name": "Core"}}
        assert _block_id_to_component_id("F3", FakeConfig(), model) == "COMP-CORE"
```

**Step 2: Run tests — expect FAIL** (signature mismatch)

**Step 3: Implement**

```python
def _block_id_to_component_id(
    block_id: str,
    config,
    model: "ArchitectureModel | None" = None,
) -> str:
    """Map F-block ID to component ID, preferring model lookup over convention."""
    if model is not None:
        for comp in model.entities.components:
            if getattr(comp, "f_block", None) == block_id:
                return comp.id
    block_def = config.fblock_dict.get(block_id, {})
    name = block_def.get("name", block_id)
    return f"COMP-{name.upper().replace(' ', '-')}"
```

Update `generate_recursive_manifests` to load model:
```python
def generate_recursive_manifests(project_root: Path, parent_model: str = ".architecture-model.yaml"):
    config = get_config(project_root)
    model = None
    model_path = project_root / parent_model
    if model_path.exists():
        try:
            from architecture_model import load_model
            model = load_model(model_path)
        except Exception:
            pass
    results = []
    for block_id, block_def in config.fblock_dict.items():
        manifest = generate_block_manifest(project_root, block_id, block_def)
        component_id = _block_id_to_component_id(block_id, config, model)
        results.append(RecursiveManifest(
            block_id=block_id, block_name=block_def.get("name", block_id),
            parent_model=parent_model, component_id=component_id, manifest=manifest,
        ))
    return results
```

**Step 4: Run tests — expect PASS**

**Step 5: Full suite pass**

**Step 6: Commit**

```bash
git add src/architecture_model/manifest/recursive.py tests/test_recursive_model_aware.py
git commit -m "feat: model-aware component ID resolution in recursive manifests"
```

---

## Task 4: Split core/decomposer.py into Focused Modules

**Files:**
- Modify: `src/architecture_model/core/decomposer.py` → keep complexity scoring + system identification
- Create: `src/architecture_model/core/test_affinity.py` → `Subsystem` + `test_affinity_decompose` + helpers
- Create: `src/architecture_model/core/fblock_assign.py` → `auto_assign_f_blocks` + helpers
- Modify: `src/architecture_model/__init__.py` → update import

**Step 1: Create `core/test_affinity.py`**

Move `Subsystem` dataclass + `test_affinity_decompose()` + all AST walking/grouping/toposort helpers. Docstring:
```python
"""Test-affinity-based repository decomposition.

Groups source files into subsystems based on which test files import them.
Bottom-up view of module boundaries from test coverage.
"""
```

**Step 2: Create `core/fblock_assign.py`**

Move `auto_assign_f_blocks()` + graph clustering helpers. Docstring:
```python
"""Automatic F-block assignment via dependency-graph clustering.

Bootstrap utility for models without f_block annotations.
Uses greedy modularity optimization on the import graph.
"""
```

**Step 3: Slim `core/decomposer.py`**

Keep: `SYSTEM_THRESHOLD`, `SystemCandidate`, `compute_complexity`, `identify_systems`, `decompose_model`, `DecompositionResult`.

Update docstring:
```python
"""Complexity scoring and system identification for architecture decomposition.

Bootstrap strategy for repos without existing models.
For repos WITH models, use orchestration.decompose instead.
"""
```

Add re-exports at bottom:
```python
from architecture_model.core.test_affinity import test_affinity_decompose  # noqa: F401
from architecture_model.core.fblock_assign import auto_assign_f_blocks  # noqa: F401
```

**Step 4: Update `__init__.py`**

```python
from architecture_model.core.test_affinity import test_affinity_decompose
```

**Step 5: Run full suite — all pass**

**Step 6: Commit**

```bash
git add src/architecture_model/core/decomposer.py \
        src/architecture_model/core/test_affinity.py \
        src/architecture_model/core/fblock_assign.py \
        src/architecture_model/__init__.py
git commit -m "refactor: split decomposer.py into focused modules (test_affinity, fblock_assign)"
```

---

## Task 5: Regenerate Sub-Models for Completeness

**Step 1: Verify COMP-PROFILES and COMP-UTILS have `files` populated**

**Step 2: Run decompose**

```bash
/opt/anaconda3/bin/python -m architecture_model decompose . -o .architecture-models
```

**Step 3: Verify 8 sub-models exist** (all except spec)

```bash
ls .architecture-models/
# Expected: cli/ config/ core/ extract/ manifest/ orchestration/ profiles/ utils/
```

**Step 4: Validate each**

```python
from pathlib import Path
from architecture_model import load_model, validate_model
for d in sorted(Path('.architecture-models').iterdir()):
    if d.is_dir() and (d / '.architecture-model.yaml').exists():
        r = validate_model(load_model(d / '.architecture-model.yaml'))
        print(f'{d.name}: {r.score}/100')
```

**Step 5: Commit**

```bash
git add .architecture-models/
git commit -m "chore: regenerate sub-models (add profiles, utils)"
```

---

## Summary

| Task | Effort | Impact |
|------|--------|--------|
| 1. Fix non-determinism | 5 min | Enables reliable staleness detection |
| 2. Set manifest_hash | 5 min | Coverage 80% → 100% |
| 3. Model-aware recursive | 20 min | Accurate component mapping for any repo |
| 4. Split decomposer | 30 min | Clear API: bootstrap vs production paths |
| 5. Regenerate sub-models | 5 min | Complete self-model coverage |

**Total: ~65 min**

## Expected Outcome

- **Validation: 98/100** (Core sig coverage warning — cosmetic)
- **Coverage: 100%** (all 5 checks including staleness)
- **Deterministic manifests** across processes
- **Self-model complete** with 8/9 sub-models (spec excluded by design)
- **Clean decomposer API** with clear bootstrap vs production lifecycle
