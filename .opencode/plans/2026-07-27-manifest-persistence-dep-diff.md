# Recursive Manifest Persistence + Dependency Diff + Sub-Model Integration

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Persist recursive manifests alongside sub-models, replace the relationship accuracy coverage check with a precise F-block dependency diff, and link sub-models to their manifests via `manifest_path`.

**Architecture:** Three changes: (1) CLI `manifest --recursive` writes to `.architecture-models/`, (2) coverage check uses `compute_block_dependencies()` for precise F-block-level comparison, (3) decompose sets `meta.manifest_path` if the manifest JSON exists.

**Tech Stack:** Python 3.12, dataclasses, JSON, YAML, pytest

**Target repo:** `/Users/baigm2/Documents/Projects/architecture-model-standard`

---

## Task 1: Persist Recursive Manifests to .architecture-models/

**Files:**
- Modify: `src/architecture_model/cli/main.py` (update `--recursive` output default)
- Test manually via CLI

**Step 1:** Run the CLI to write recursive manifests alongside sub-models:
```bash
/opt/anaconda3/bin/python -m architecture_model manifest . --recursive -o .architecture-models
```

**Step 2:** Verify output:
```bash
ls .architecture-models/F*/manifest.json
```
Expected: 9 manifest.json files (F1-F9)

**Step 3:** Commit:
```bash
git add .architecture-models/*/manifest.json
git commit -m "chore: persist recursive manifests to .architecture-models/"
```

---

## Task 2: Dependency Diff Coverage Check

**Files:**
- Modify: `src/architecture_model/core/coverage.py:96-148` (replace `_check_relationship_accuracy`)
- Create: `tests/test_dependency_diff.py`

**Step 1: Write failing test**

```python
"""Tests for F-block dependency diff coverage check."""
from architecture_model.core.coverage import _check_dependency_accuracy
from architecture_model.core.types import (
    ArchitectureModel, Component, Entities, ModelMeta, Relationship, RelationType, Status,
)


def _model_with_deps(deps: list[tuple[str, str]], components: list[Component]):
    rels = [Relationship(from_id=f, to_id=t, type=RelationType.DEPENDS_ON) for f, t in deps]
    return ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="2.0"),
        entities=Entities(components=components),
        relationships=rels,
    )


def test_perfect_match():
    comps = [
        Component(id="COMP-A", name="A", f_block="F1", status=Status.ACTIVE),
        Component(id="COMP-B", name="B", f_block="F2", status=Status.ACTIVE),
    ]
    model = _model_with_deps([("COMP-A", "COMP-B")], comps)
    import_deps = {"F1": {"F2"}}
    check = _check_dependency_accuracy(model, import_deps)
    assert check.score == 100.0


def test_missing_from_model():
    comps = [
        Component(id="COMP-A", name="A", f_block="F1", status=Status.ACTIVE),
        Component(id="COMP-B", name="B", f_block="F2", status=Status.ACTIVE),
        Component(id="COMP-C", name="C", f_block="F3", status=Status.ACTIVE),
    ]
    model = _model_with_deps([("COMP-A", "COMP-B")], comps)
    import_deps = {"F1": {"F2", "F3"}}  # F1->F3 in imports but not model
    check = _check_dependency_accuracy(model, import_deps)
    assert check.score < 100.0
    assert any("F3" in m for m in check.missing)


def test_extra_in_model():
    comps = [
        Component(id="COMP-A", name="A", f_block="F1", status=Status.ACTIVE),
        Component(id="COMP-B", name="B", f_block="F2", status=Status.ACTIVE),
    ]
    model = _model_with_deps([("COMP-A", "COMP-B")], comps)
    import_deps = {}  # no imports found
    check = _check_dependency_accuracy(model, import_deps)
    assert any("F2" in e for e in check.extra)


def test_no_deps_scores_100():
    comps = [Component(id="COMP-A", name="A", f_block="F1", status=Status.ACTIVE)]
    model = _model_with_deps([], comps)
    import_deps = {}
    check = _check_dependency_accuracy(model, import_deps)
    assert check.score == 100.0
```

**Step 2: Implement `_check_dependency_accuracy`**

Replace `_check_relationship_accuracy` in coverage.py with:

```python
def _check_dependency_accuracy(
    model: "ArchitectureModel",
    import_deps: dict[str, set[str]] | None = None,
    manifest: dict | None = None,
) -> CoverageCheck:
    """Check model depends-on relationships against import-derived F-block dependencies.
    
    If import_deps not provided, falls back to old interface-based check using manifest.
    """
    if import_deps is None and manifest is not None:
        # Fallback: derive from manifest interfaces (old behavior)
        return _check_relationship_accuracy_legacy(model, manifest)
    
    if import_deps is None:
        import_deps = {}

    # Build model edges as F-block pairs
    comp_to_fb = {c.id: c.f_block for c in model.entities.components if c.f_block}
    model_edges: set[tuple[str, str]] = set()
    for rel in model.relationships:
        if rel.type == RelationType.DEPENDS_ON:
            src_fb = comp_to_fb.get(rel.from_id)
            tgt_fb = comp_to_fb.get(rel.to_id)
            if src_fb and tgt_fb:
                model_edges.add((src_fb, tgt_fb))

    # Build import edges
    import_edges: set[tuple[str, str]] = set()
    for src_fb, targets in import_deps.items():
        for tgt_fb in targets:
            import_edges.add((src_fb, tgt_fb))

    all_edges = model_edges | import_edges
    if not all_edges:
        return CoverageCheck(name="Dependency Accuracy", score=100.0, matched=0, total=0)

    matched = model_edges & import_edges
    missing = sorted(import_edges - model_edges)  # in imports but not model
    extra = sorted(model_edges - import_edges)    # in model but not imports

    score = len(matched) / len(all_edges) * 100

    return CoverageCheck(
        name="Dependency Accuracy",
        score=score,
        matched=len(matched),
        total=len(all_edges),
        missing=[f"{a} → {b}" for a, b in missing],
        extra=[f"{a} → {b}" for a, b in extra],
    )
```

Keep the old function as `_check_relationship_accuracy_legacy` (renamed from `_check_relationship_accuracy`).

**Step 3:** Update `coverage_report()` to use the new check:
- Accept optional `import_deps` parameter
- Pass it to `_check_dependency_accuracy` instead of calling `_check_relationship_accuracy`
- If `import_deps` is None, fall back to legacy behavior (so existing callers still work)

**Step 4: Run tests, commit**

---

## Task 3: Sub-Model Integration (manifest_path in meta)

**Files:**
- Modify: `src/architecture_model/orchestration/decompose.py:275` (add manifest_path to meta)
- Modify: `src/architecture_model/core/types.py` (add `manifest_path` to `ModelMeta` if not present)
- Test: `tests/test_decompose.py` (add assertion)

**Step 1:** Add `manifest_path: str = ""` to `ModelMeta` dataclass if not already there.

**Step 2:** In `decompose_model()`, after building the sub-model (line ~274), check if manifest exists and set path:
```python
manifest_json = output_dir / block_id / "manifest.json" if output_dir else None
manifest_path = f"{block_id}/manifest.json" if (manifest_json and manifest_json.exists()) else ""
```
Add `manifest_path=manifest_path` to the ModelMeta constructor.

**Step 3:** Regenerate sub-models, verify manifest_path is set.

**Step 4:** Commit.
