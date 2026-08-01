# Architecture Documentation Generator — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deterministic generation of 6 standard SE document types from architecture model data. All docs are Markdown files, generated mechanically (no LLM), reproducible (same model → same docs).

**Architecture:** New `docs/` module in `architecture-model-standard` with per-doc-type generators + orchestrator. Each generator takes model data and returns a Markdown string. The orchestrator writes all docs to `.architecture-models/docs/`.

**Tech Stack:** Python 3.12, Markdown (GFM), Mermaid

**Python:** `/opt/anaconda3/bin/python`
**Pytest:** `/opt/anaconda3/bin/python -m pytest`
**Repo root:** `/Users/baigm2/Documents/Projects/architecture-model-standard`

**Always:** `--ignore=tests/test_config_loader.py`

---

## Output Structure

```
.architecture-models/
├── docs/
│   ├── README.md                    ← Index with links to all docs
│   ├── diagrams/
│   │   ├── context.mmd             ← System context (actors → system)
│   │   ├── components.mmd          ← Component map (layers, capabilities)
│   │   ├── dependencies.mmd        ← Dependency graph (f-blocks)
│   │   └── behaviors.mmd           ← Behavior flows
│   ├── components/
│   │   ├── COMP-1.md               ← Per-component spec sheet
│   │   ├── COMP-2.md
│   │   └── ...
│   ├── icd.md                       ← Interface Control Document
│   ├── dependency-matrix.md         ← NxN component dependency table
│   ├── health.md                    ← Metrics, confidence, coherence
│   └── drift.md                     ← Changes since last extraction (if previous model available)
```

---

## Module Structure

```
src/architecture_model/docs/
├── __init__.py                      ← exports generate_docs()
├── generator.py                     ← orchestrator
├── component_spec.py                ← per-component spec sheet
├── dependency_matrix.py             ← NxN table
├── icd.py                           ← interface control document
├── health.py                        ← health/metrics report
├── drift.py                         ← change log from diff
└── index.py                         ← README generator
```

---

### Task 1: Orchestrator + Component Spec Sheet

The component spec is the most data-rich doc and exercises most model fields.

**Files:**
- Create: `src/architecture_model/docs/__init__.py`
- Create: `src/architecture_model/docs/generator.py`
- Create: `src/architecture_model/docs/component_spec.py`
- Test: `tests/test_docs_generator.py`

**Step 1: Write failing tests**

Create `tests/test_docs_generator.py`:

```python
"""Test deterministic doc generation from model data."""
import textwrap
from pathlib import Path

import pytest

from architecture_model.core.types import (
    ArchitectureModel, Component, Entities, FunctionSignature,
    ModelMeta, Symbol, SymbolKind, TestContract, ComponentInterface,
)
from architecture_model.docs.component_spec import generate_component_spec
from architecture_model.docs.generator import generate_docs


@pytest.fixture
def sample_model():
    return ArchitectureModel(
        meta=ModelMeta(project="test-project", schema_version="1.3"),
        entities=Entities(components=[
            Component(
                id="COMP-1", name="JsonProvider", status="ACTIVE",
                f_block="F1", pattern="provider",
                files=["src/flask/json/__init__.py", "src/flask/json/provider.py"],
                contract="Provides JSON serialization for Flask applications.",
                responsibilities=["serialize", "deserialize", "configure"],
                signatures=[
                    FunctionSignature(name="dumps", params=["obj", "**kwargs"], returns="str",
                                    docstring="Serialize obj to JSON string."),
                    FunctionSignature(name="loads", params=["s", "**kwargs"], returns="Any",
                                    docstring="Deserialize JSON string."),
                ],
                symbols=[
                    Symbol(name="JSONProvider", kind=SymbolKind.CLASS,
                          bases=["object"], methods=["dumps", "loads", "response"]),
                ],
                interfaces=[
                    ComponentInterface(name="json_api", kind="provides",
                                     target_component="COMP-2", symbols=["dumps", "loads"]),
                ],
                test_contracts=[
                    TestContract(test_file="test_json.py", test_method="test_dumps",
                               assertion="result == '{}'", contract_type="value_equality"),
                ],
                confidence=0.85,
            ),
            Component(
                id="COMP-2", name="Router", status="ACTIVE",
                f_block="F1", pattern="router",
                files=["src/flask/routing.py"],
                contract="URL routing and dispatch.",
                interfaces=[
                    ComponentInterface(name="json_dep", kind="requires",
                                     target_component="COMP-1", symbols=["dumps"]),
                ],
                confidence=0.72,
            ),
        ]),
        relationships=[],
    )


class TestComponentSpec:
    def test_generates_markdown(self, sample_model):
        comp = sample_model.entities.components[0]
        md = generate_component_spec(comp, sample_model)
        assert "# COMP-1: JsonProvider" in md
        assert "ACTIVE" in md
        assert "provider" in md

    def test_includes_contract(self, sample_model):
        comp = sample_model.entities.components[0]
        md = generate_component_spec(comp, sample_model)
        assert "JSON serialization" in md

    def test_includes_signatures(self, sample_model):
        comp = sample_model.entities.components[0]
        md = generate_component_spec(comp, sample_model)
        assert "dumps" in md
        assert "loads" in md
        assert "str" in md  # return type

    def test_includes_dependencies(self, sample_model):
        comp = sample_model.entities.components[0]
        md = generate_component_spec(comp, sample_model)
        assert "COMP-2" in md or "Router" in md

    def test_includes_test_contracts(self, sample_model):
        comp = sample_model.entities.components[0]
        md = generate_component_spec(comp, sample_model)
        assert "test_json.py" in md

    def test_deterministic(self, sample_model):
        comp = sample_model.entities.components[0]
        md1 = generate_component_spec(comp, sample_model)
        md2 = generate_component_spec(comp, sample_model)
        assert md1 == md2


class TestDocGenerator:
    def test_generates_all_docs(self, sample_model, tmp_path):
        result = generate_docs(sample_model, output_dir=tmp_path)
        assert (tmp_path / "README.md").exists()
        assert (tmp_path / "components" / "COMP-1.md").exists()
        assert (tmp_path / "components" / "COMP-2.md").exists()

    def test_returns_generated_paths(self, sample_model, tmp_path):
        result = generate_docs(sample_model, output_dir=tmp_path)
        assert "components" in result
        assert "index" in result
```

**Step 2: Run to confirm failure**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_docs_generator.py -v --ignore=tests/test_config_loader.py`

**Step 3: Implement component_spec.py**

```python
"""Generate per-component specification sheets."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel, Component


def generate_component_spec(comp: "Component", model: "ArchitectureModel") -> str:
    """Generate a markdown spec sheet for a single component."""
    lines = []

    # Header
    lines.append(f"# {comp.id}: {comp.name}")
    lines.append("")
    meta_parts = []
    if comp.status:
        meta_parts.append(f"**Status:** {comp.status}")
    if comp.pattern:
        meta_parts.append(f"**Pattern:** {comp.pattern}")
    if comp.f_block:
        meta_parts.append(f"**F-block:** {comp.f_block}")
    if comp.confidence:
        meta_parts.append(f"**Confidence:** {comp.confidence:.0%}")
    lines.append(" | ".join(meta_parts))
    lines.append("")

    # Files
    if comp.files:
        lines.append("## Files")
        lines.append("")
        for f in sorted(comp.files):
            lines.append(f"- `{f}`")
        lines.append("")

    # Contract
    if comp.contract:
        lines.append("## Contract")
        lines.append("")
        lines.append(comp.contract)
        lines.append("")

    # Responsibilities
    if comp.responsibilities:
        lines.append("## Responsibilities")
        lines.append("")
        for r in comp.responsibilities:
            lines.append(f"- {r}")
        lines.append("")

    # Public API (signatures)
    if comp.signatures:
        lines.append("## Public API")
        lines.append("")
        lines.append("| Function | Parameters | Returns | Description |")
        lines.append("|----------|-----------|---------|-------------|")
        for sig in comp.signatures:
            params = ", ".join(sig.params) if sig.params else ""
            returns = sig.returns or "None"
            doc = (sig.docstring or "")[:80]
            lines.append(f"| `{sig.name}` | `{params}` | `{returns}` | {doc} |")
        lines.append("")

    # Symbols (classes)
    if comp.symbols:
        lines.append("## Classes")
        lines.append("")
        lines.append("| Class | Kind | Bases | Members |")
        lines.append("|-------|------|-------|---------|")
        for sym in comp.symbols:
            bases = ", ".join(sym.bases) if sym.bases else "—"
            members = ", ".join(sym.methods[:5]) if sym.methods else "—"
            if len(sym.methods) > 5:
                members += f" (+{len(sym.methods) - 5})"
            lines.append(f"| `{sym.name}` | {sym.kind.value if hasattr(sym.kind, 'value') else sym.kind} | {bases} | {members} |")
        lines.append("")

    # Dependencies (interfaces)
    if comp.interfaces:
        provides = [i for i in comp.interfaces if i.kind == "provides"]
        requires = [i for i in comp.interfaces if i.kind == "requires"]

        if provides or requires:
            lines.append("## Dependencies")
            lines.append("")
            if provides:
                lines.append("**Provides to:**")
                for iface in provides:
                    syms = ", ".join(iface.symbols[:5]) if iface.symbols else ""
                    target_name = _resolve_name(iface.target_component, model)
                    lines.append(f"- {target_name}: `{syms}`")
                lines.append("")
            if requires:
                lines.append("**Requires from:**")
                for iface in requires:
                    syms = ", ".join(iface.symbols[:5]) if iface.symbols else ""
                    target_name = _resolve_name(iface.target_component, model)
                    lines.append(f"- {target_name}: `{syms}`")
                lines.append("")

    # Test Coverage
    if comp.test_contracts:
        lines.append("## Test Coverage")
        lines.append("")
        lines.append(f"**{len(comp.test_contracts)} test contracts**")
        lines.append("")
        for tc in comp.test_contracts[:20]:  # Cap at 20
            lines.append(f"- `{tc.test_file}::{tc.test_method}` — {tc.contract_type}: `{tc.assertion[:60]}`")
        if len(comp.test_contracts) > 20:
            lines.append(f"- ... and {len(comp.test_contracts) - 20} more")
        lines.append("")

    return "\n".join(lines)


def _resolve_name(comp_id: str, model: "ArchitectureModel") -> str:
    """Resolve component ID to 'ID (Name)' string."""
    components = model.entities.components if hasattr(model.entities, 'components') else []
    for c in components:
        if c.id == comp_id:
            return f"{c.id} ({c.name})"
    return comp_id
```

**Step 4: Implement generator.py**

```python
"""Orchestrator for generating all architecture documentation."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel
    from architecture_model.manifest.types import Manifest

from architecture_model.docs.component_spec import generate_component_spec


def generate_docs(
    model: "ArchitectureModel",
    output_dir: Path,
    manifest: "Manifest | None" = None,
    previous_model: "ArchitectureModel | None" = None,
) -> dict[str, list[Path]]:
    """Generate all documentation from model data.

    Returns dict of doc category -> list of generated file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, list[Path]] = {}

    # Component spec sheets
    comp_dir = output_dir / "components"
    comp_dir.mkdir(exist_ok=True)
    comp_paths = []
    components = model.entities.components if hasattr(model.entities, 'components') else []
    for comp in components:
        md = generate_component_spec(comp, model)
        path = comp_dir / f"{comp.id}.md"
        path.write_text(md)
        comp_paths.append(path)
    result["components"] = comp_paths

    # Diagrams
    diag_dir = output_dir / "diagrams"
    diag_dir.mkdir(exist_ok=True)
    try:
        from architecture_model.core.visualize import generate_all_diagrams
        diag_paths = generate_all_diagrams(model, diag_dir)
        result["diagrams"] = list(diag_paths.values())
    except Exception:
        result["diagrams"] = []

    # Dependency matrix
    from architecture_model.docs.dependency_matrix import generate_dependency_matrix
    dm_md = generate_dependency_matrix(model)
    dm_path = output_dir / "dependency-matrix.md"
    dm_path.write_text(dm_md)
    result["dependency_matrix"] = [dm_path]

    # ICD
    from architecture_model.docs.icd import generate_icd
    icd_md = generate_icd(model)
    icd_path = output_dir / "icd.md"
    icd_path.write_text(icd_md)
    result["icd"] = [icd_path]

    # Health report
    from architecture_model.docs.health import generate_health_report
    health_md = generate_health_report(model, manifest)
    health_path = output_dir / "health.md"
    health_path.write_text(health_md)
    result["health"] = [health_path]

    # Drift report (only if previous model provided)
    if previous_model:
        from architecture_model.docs.drift import generate_drift_report
        drift_md = generate_drift_report(previous_model, model)
        drift_path = output_dir / "drift.md"
        drift_path.write_text(drift_md)
        result["drift"] = [drift_path]

    # Index
    from architecture_model.docs.index import generate_index
    index_md = generate_index(model, result)
    index_path = output_dir / "README.md"
    index_path.write_text(index_md)
    result["index"] = [index_path]

    return result
```

**Step 5: Implement __init__.py**

```python
"""Architecture documentation generators."""
from architecture_model.docs.generator import generate_docs

__all__ = ["generate_docs"]
```

**Step 6: Run tests, verify pass**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_docs_generator.py -v --ignore=tests/test_config_loader.py`

**Step 7: Commit**

```bash
git add src/architecture_model/docs/ tests/test_docs_generator.py
git commit -m "feat: add component spec sheet + doc generator orchestrator"
```

---

### Task 2: Dependency Matrix

**Files:**
- Create: `src/architecture_model/docs/dependency_matrix.py`
- Test: add to `tests/test_docs_generator.py`

**Step 1: Add tests**

```python
class TestDependencyMatrix:
    def test_generates_table(self, sample_model):
        from architecture_model.docs.dependency_matrix import generate_dependency_matrix
        md = generate_dependency_matrix(sample_model)
        assert "COMP-1" in md or "JsonProvider" in md
        assert "COMP-2" in md or "Router" in md

    def test_shows_direction(self, sample_model):
        from architecture_model.docs.dependency_matrix import generate_dependency_matrix
        md = generate_dependency_matrix(sample_model)
        # Should show that Router requires from JsonProvider
        assert "→" in md or "provides" in md.lower() or "requires" in md.lower()

    def test_deterministic(self, sample_model):
        from architecture_model.docs.dependency_matrix import generate_dependency_matrix
        assert generate_dependency_matrix(sample_model) == generate_dependency_matrix(sample_model)
```

**Step 2: Implement dependency_matrix.py**

```python
"""Generate NxN component dependency matrix."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel


def generate_dependency_matrix(model: "ArchitectureModel") -> str:
    """Generate an NxN dependency matrix as markdown table."""
    components = model.entities.components if hasattr(model.entities, 'components') else []
    if not components:
        return "# Dependency Matrix\n\nNo components found.\n"

    lines = ["# Dependency Matrix", ""]

    # Build adjacency: provider_id -> set of consumer_ids
    provides_to: dict[str, set[str]] = {}  # comp_id -> set of comp_ids it provides to
    requires_from: dict[str, set[str]] = {}  # comp_id -> set of comp_ids it requires from

    for comp in components:
        if not comp.interfaces:
            continue
        for iface in comp.interfaces:
            if iface.kind == "provides" and iface.target_component:
                provides_to.setdefault(comp.id, set()).add(iface.target_component)
            elif iface.kind == "requires" and iface.target_component:
                requires_from.setdefault(comp.id, set()).add(iface.target_component)

    # Also check relationships
    for rel in (model.relationships or []):
        rel_type = rel.type if hasattr(rel, 'type') else str(rel.get('type', ''))
        if 'depends' in str(rel_type).lower() or 'uses' in str(rel_type).lower():
            from_id = rel.from_id if hasattr(rel, 'from_id') else rel.get('from', '')
            to_id = rel.to_id if hasattr(rel, 'to_id') else rel.get('to', '')
            requires_from.setdefault(from_id, set()).add(to_id)

    # Filter to components with any edges
    active_ids = set()
    for k, v in provides_to.items():
        active_ids.add(k)
        active_ids.update(v)
    for k, v in requires_from.items():
        active_ids.add(k)
        active_ids.update(v)

    if not active_ids:
        lines.append("No dependencies detected between components.")
        lines.append("")
        return "\n".join(lines)

    # Build matrix
    active_comps = [c for c in components if c.id in active_ids]
    active_comps.sort(key=lambda c: c.id)

    # Header
    header = "| | " + " | ".join(f"**{c.name}**" for c in active_comps) + " |"
    sep = "|---|" + "|".join("---" for _ in active_comps) + "|"
    lines.append(header)
    lines.append(sep)

    # Rows: row=consumer, col=provider. Cell shows → if row requires from col
    for row_comp in active_comps:
        cells = []
        for col_comp in active_comps:
            if row_comp.id == col_comp.id:
                cells.append("·")
            elif col_comp.id in requires_from.get(row_comp.id, set()):
                cells.append("→")  # row requires from col
            elif row_comp.id in requires_from.get(col_comp.id, set()):
                cells.append("←")  # col requires from row (row provides to col)
            else:
                cells.append("")
        lines.append(f"| **{row_comp.name}** | " + " | ".join(cells) + " |")

    lines.append("")
    lines.append("**Legend:** → = requires from (column), ← = provides to (column), · = self")
    lines.append("")

    return "\n".join(lines)
```

**Step 3: Run tests, verify, commit**

```bash
git add src/architecture_model/docs/dependency_matrix.py tests/test_docs_generator.py
git commit -m "feat: add dependency matrix doc generator"
```

---

### Task 3: ICD (Interface Control Document)

**Files:**
- Create: `src/architecture_model/docs/icd.py`
- Test: add to `tests/test_docs_generator.py`

**Step 1: Add tests**

```python
class TestICD:
    def test_generates_interface_entries(self, sample_model):
        from architecture_model.docs.icd import generate_icd
        md = generate_icd(sample_model)
        assert "JsonProvider" in md or "COMP-1" in md
        assert "dumps" in md or "loads" in md

    def test_shows_provider_and_consumer(self, sample_model):
        from architecture_model.docs.icd import generate_icd
        md = generate_icd(sample_model)
        assert "Provider" in md or "provides" in md.lower()
        assert "Consumer" in md or "requires" in md.lower()
```

**Step 2: Implement icd.py**

Generate a per-interface-pair section showing:
- Provider component → Consumer component
- Symbols exchanged
- Signatures of exchanged symbols (from provider's signatures list)

```python
"""Generate Interface Control Document."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel


def generate_icd(model: "ArchitectureModel") -> str:
    """Generate ICD documenting all inter-component interfaces."""
    lines = ["# Interface Control Document", ""]
    lines.append(f"**Project:** {model.meta.project}")
    lines.append(f"**Schema Version:** {model.meta.schema_version}")
    lines.append("")

    components = model.entities.components if hasattr(model.entities, 'components') else []
    comp_map = {c.id: c for c in components}

    # Collect all interface pairs
    interfaces = []  # (provider_comp, consumer_comp, symbols, signatures)
    for comp in components:
        if not comp.interfaces:
            continue
        for iface in comp.interfaces:
            if iface.kind == "provides" and iface.target_component:
                consumer = comp_map.get(iface.target_component)
                provider = comp
                syms = iface.symbols or []
                # Find matching signatures
                sigs = [s for s in (comp.signatures or []) if s.name in syms]
                interfaces.append((provider, consumer, syms, sigs))

    if not interfaces:
        lines.append("No inter-component interfaces detected.")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"**Total Interfaces:** {len(interfaces)}")
    lines.append("")

    # Group by provider
    by_provider: dict[str, list] = {}
    for provider, consumer, syms, sigs in interfaces:
        by_provider.setdefault(provider.id, []).append((provider, consumer, syms, sigs))

    for provider_id, entries in sorted(by_provider.items()):
        provider = comp_map[provider_id]
        lines.append(f"## {provider.name} ({provider.id})")
        lines.append("")
        lines.append(f"**Contract:** {provider.contract or 'N/A'}")
        lines.append("")

        for _, consumer, syms, sigs in entries:
            consumer_name = f"{consumer.name} ({consumer.id})" if consumer else "Unknown"
            lines.append(f"### → {consumer_name}")
            lines.append("")
            lines.append(f"**Symbols:** {', '.join(f'`{s}`' for s in syms) if syms else 'N/A'}")
            lines.append("")

            if sigs:
                lines.append("| Function | Signature | Description |")
                lines.append("|----------|-----------|-------------|")
                for sig in sigs:
                    params = ", ".join(sig.params) if sig.params else ""
                    doc = (sig.docstring or "")[:60]
                    lines.append(f"| `{sig.name}` | `({params}) → {sig.returns or 'None'}` | {doc} |")
                lines.append("")

    return "\n".join(lines)
```

**Step 3: Run, verify, commit**

```bash
git add src/architecture_model/docs/icd.py tests/test_docs_generator.py
git commit -m "feat: add ICD doc generator"
```

---

### Task 4: Health Report

**Files:**
- Create: `src/architecture_model/docs/health.py`
- Test: add to `tests/test_docs_generator.py`

**Step 1: Add tests**

```python
class TestHealthReport:
    def test_includes_confidence(self, sample_model):
        from architecture_model.docs.health import generate_health_report
        md = generate_health_report(sample_model)
        assert "Confidence" in md or "confidence" in md
        assert "85%" in md or "0.85" in md

    def test_includes_component_table(self, sample_model):
        from architecture_model.docs.health import generate_health_report
        md = generate_health_report(sample_model)
        assert "JsonProvider" in md
        assert "Router" in md
```

**Step 2: Implement health.py**

Generate:
- Summary stats (component count, avg confidence, field fill rates)
- Per-component table (name, confidence, signatures, symbols, tests, pattern)
- Confidence distribution buckets
- Field completeness breakdown

```python
"""Generate health metrics report."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel
    from architecture_model.manifest.types import Manifest


def generate_health_report(model: "ArchitectureModel", manifest: "Manifest | None" = None) -> str:
    """Generate architecture health metrics as markdown."""
    lines = ["# Architecture Health Report", ""]
    lines.append(f"**Project:** {model.meta.project}")
    lines.append("")

    components = model.entities.components if hasattr(model.entities, 'components') else []
    if not components:
        lines.append("No components found.")
        return "\n".join(lines)

    # Summary
    avg_conf = sum(c.confidence or 0 for c in components) / len(components)
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Components | {len(components)} |")
    lines.append(f"| Avg Confidence | {avg_conf:.0%} |")
    lines.append(f"| With Signatures | {sum(1 for c in components if c.signatures)}/{len(components)} |")
    lines.append(f"| With Symbols | {sum(1 for c in components if c.symbols)}/{len(components)} |")
    lines.append(f"| With Test Contracts | {sum(1 for c in components if c.test_contracts)}/{len(components)} |")
    lines.append(f"| With Pattern | {sum(1 for c in components if c.pattern)}/{len(components)} |")
    lines.append(f"| With Interfaces | {sum(1 for c in components if c.interfaces)}/{len(components)} |")
    lines.append("")

    # Confidence distribution
    buckets = {"≥90%": 0, "70-89%": 0, "50-69%": 0, "30-49%": 0, "<30%": 0}
    for c in components:
        conf = c.confidence or 0
        if conf >= 0.9: buckets["≥90%"] += 1
        elif conf >= 0.7: buckets["70-89%"] += 1
        elif conf >= 0.5: buckets["50-69%"] += 1
        elif conf >= 0.3: buckets["30-49%"] += 1
        else: buckets["<30%"] += 1

    lines.append("## Confidence Distribution")
    lines.append("")
    lines.append("| Bucket | Count | Bar |")
    lines.append("|--------|-------|-----|")
    for bucket, count in buckets.items():
        bar = "█" * count
        lines.append(f"| {bucket} | {count} | {bar} |")
    lines.append("")

    # Per-component table
    lines.append("## Per-Component Metrics")
    lines.append("")
    lines.append("| Component | Confidence | Sigs | Symbols | Tests | Pattern | Files |")
    lines.append("|-----------|-----------|------|---------|-------|---------|-------|")
    for c in sorted(components, key=lambda x: -(x.confidence or 0)):
        conf = f"{c.confidence:.0%}" if c.confidence else "—"
        sigs = len(c.signatures) if c.signatures else 0
        syms = len(c.symbols) if c.symbols else 0
        tests = len(c.test_contracts) if c.test_contracts else 0
        pattern = c.pattern or "—"
        files = len(c.files) if c.files else 0
        lines.append(f"| {c.name} | {conf} | {sigs} | {syms} | {tests} | {pattern} | {files} |")
    lines.append("")

    # Low confidence components (actionable)
    low_conf = [c for c in components if (c.confidence or 0) < 0.5]
    if low_conf:
        lines.append("## Action Items (Low Confidence)")
        lines.append("")
        for c in low_conf:
            missing = []
            if not c.signatures: missing.append("signatures")
            if not c.symbols: missing.append("symbols")
            if not c.test_contracts: missing.append("test_contracts")
            if not c.pattern: missing.append("pattern")
            if not c.contract: missing.append("contract")
            lines.append(f"- **{c.name}** ({c.confidence:.0%}): missing {', '.join(missing)}")
        lines.append("")

    return "\n".join(lines)
```

**Step 3: Run, verify, commit**

```bash
git add src/architecture_model/docs/health.py tests/test_docs_generator.py
git commit -m "feat: add health report doc generator"
```

---

### Task 5: Drift Report

**Files:**
- Create: `src/architecture_model/docs/drift.py`
- Test: add to `tests/test_docs_generator.py`

**Step 1: Add tests**

```python
class TestDriftReport:
    def test_detects_added_component(self, sample_model):
        from copy import deepcopy
        from architecture_model.docs.drift import generate_drift_report
        from architecture_model.core.types import Component

        old = deepcopy(sample_model)
        old.entities.components = [old.entities.components[0]]  # Only COMP-1

        md = generate_drift_report(old, sample_model)
        assert "Added" in md or "added" in md
        assert "Router" in md or "COMP-2" in md

    def test_no_changes(self, sample_model):
        from architecture_model.docs.drift import generate_drift_report
        md = generate_drift_report(sample_model, sample_model)
        assert "No changes" in md or "no drift" in md.lower()
```

**Step 2: Implement drift.py**

Wrap the existing `differ.py` and format as markdown:

```python
"""Generate drift/change report between model versions."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel


def generate_drift_report(old_model: "ArchitectureModel", new_model: "ArchitectureModel") -> str:
    """Generate a change report comparing two model versions."""
    from architecture_model.core.differ import diff_models

    diff = diff_models(old_model, new_model)
    lines = ["# Architecture Drift Report", ""]

    if not diff.has_changes:
        lines.append("**No changes detected.** Model is current.")
        lines.append("")
        return "\n".join(lines)

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Change Type | Count |")
    lines.append(f"|-------------|-------|")
    lines.append(f"| Added | {diff.added_count} |")
    lines.append(f"| Removed | {diff.removed_count} |")
    lines.append(f"| Modified | {diff.modified_count} |")
    lines.append("")

    # Entity changes
    if diff.entity_changes:
        lines.append("## Entity Changes")
        lines.append("")
        lines.append("| Type | Entity | Change | Details |")
        lines.append("|------|--------|--------|---------|")
        for change in diff.entity_changes:
            lines.append(f"| {change.entity_type} | {change.entity_name} ({change.entity_id}) | {change.change_type.value} | {change.details[:60]} |")
        lines.append("")

    # Relationship changes
    if diff.relationship_changes:
        lines.append("## Relationship Changes")
        lines.append("")
        lines.append("| Type | From → To | Change |")
        lines.append("|------|-----------|--------|")
        for change in diff.relationship_changes:
            lines.append(f"| {change.rel_type} | {change.from_id} → {change.to_id} | {change.change_type.value} |")
        lines.append("")

    # Affected artifacts
    affected = diff.affected_artifacts()
    if affected:
        lines.append("## Affected Documents")
        lines.append("")
        for artifact in sorted(affected):
            lines.append(f"- {artifact}")
        lines.append("")

    return "\n".join(lines)
```

**Step 3: Run, verify, commit**

```bash
git add src/architecture_model/docs/drift.py tests/test_docs_generator.py
git commit -m "feat: add drift report doc generator"
```

---

### Task 6: Index (README) Generator

**Files:**
- Create: `src/architecture_model/docs/index.py`
- Test: already covered in TestDocGenerator

**Step 1: Implement index.py**

```python
"""Generate index/README for generated documentation."""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.types import ArchitectureModel


def generate_index(model: "ArchitectureModel", doc_paths: dict[str, list[Path]]) -> str:
    """Generate README.md index linking to all generated docs."""
    lines = [f"# {model.meta.project} — Architecture Documentation", ""]

    lines.append(f"**Schema Version:** {model.meta.schema_version}")
    components = model.entities.components if hasattr(model.entities, 'components') else []
    lines.append(f"**Components:** {len(components)}")
    avg_conf = sum(c.confidence or 0 for c in components) / max(len(components), 1)
    lines.append(f"**Avg Confidence:** {avg_conf:.0%}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Diagrams
    if doc_paths.get("diagrams"):
        lines.append("## Diagrams")
        lines.append("")
        for p in doc_paths["diagrams"]:
            lines.append(f"- [{p.stem}](diagrams/{p.name})")
        lines.append("")

    # Component specs
    if doc_paths.get("components"):
        lines.append("## Component Specifications")
        lines.append("")
        for p in sorted(doc_paths["components"]):
            # Try to find component name
            comp_id = p.stem
            comp_name = comp_id
            for c in components:
                if c.id == comp_id:
                    comp_name = f"{c.name} ({c.id})"
                    break
            lines.append(f"- [{comp_name}](components/{p.name})")
        lines.append("")

    # Other docs
    other_docs = [
        ("dependency_matrix", "Dependency Matrix", "dependency-matrix.md"),
        ("icd", "Interface Control Document", "icd.md"),
        ("health", "Health Report", "health.md"),
        ("drift", "Drift Report", "drift.md"),
    ]
    lines.append("## Reference Documents")
    lines.append("")
    for key, title, filename in other_docs:
        if doc_paths.get(key):
            lines.append(f"- [{title}]({filename})")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Generated deterministically from `.architecture-model-extracted.yaml`.*")
    lines.append("")

    return "\n".join(lines)
```

**Step 2: Run full test suite, commit**

```bash
git add src/architecture_model/docs/index.py
git commit -m "feat: add index/README doc generator"
```

---

### Task 7: CLI Command (`architecture-model docs`)

**Files:**
- Modify: `src/architecture_model/cli/main.py` — add `docs` subcommand
- Test: `tests/test_docs_cli.py`

**Step 1: Add CLI handler**

In `cli/main.py`, add a `_cmd_docs(args)` function:

```python
def _cmd_docs(args):
    """Generate architecture documentation."""
    from pathlib import Path
    from architecture_model.core.parser import load_model
    from architecture_model.docs import generate_docs

    root = Path(args.repo)
    model_path = root / ".architecture-model-extracted.yaml"
    if not model_path.exists():
        model_path = root / ".architecture-model.yaml"
    if not model_path.exists():
        print(f"No model found in {root}")
        return 1

    model = load_model(model_path)
    output = root / ".architecture-models" / "docs"

    # Load manifest if available
    manifest = None
    try:
        from architecture_model.manifest.generator import generate_manifest
        manifest = generate_manifest(root)
    except Exception:
        pass

    # Load previous model for drift (if exists)
    prev_model = None
    # Could look for git history or a cached previous version

    result = generate_docs(model, output_dir=output, manifest=manifest, previous_model=prev_model)

    total = sum(len(v) for v in result.values())
    print(f"Generated {total} documents in {output}/")
    for category, paths in result.items():
        if paths:
            print(f"  {category}: {len(paths)} files")
    return 0
```

Register in argparse:
```python
docs_parser = subparsers.add_parser("docs", help="Generate architecture documentation")
docs_parser.add_argument("repo", help="Repository root path")
docs_parser.set_defaults(func=_cmd_docs)
```

**Step 2: Test**

```python
def test_docs_cli(tmp_path):
    """CLI generates docs from a model."""
    # Setup minimal model
    from architecture_model.core.types import ArchitectureModel, Component, Entities, ModelMeta
    from architecture_model.core.parser import save_model

    model = ArchitectureModel(
        meta=ModelMeta(project="test", schema_version="1.3"),
        entities=Entities(components=[
            Component(id="COMP-1", name="Core", status="ACTIVE", files=["core.py"], contract="Core logic.")
        ]),
        relationships=[],
    )
    save_model(model, tmp_path / ".architecture-model-extracted.yaml")

    from architecture_model.cli.main import _cmd_docs
    import argparse
    args = argparse.Namespace(repo=str(tmp_path))
    result = _cmd_docs(args)

    assert result == 0
    assert (tmp_path / ".architecture-models" / "docs" / "README.md").exists()
    assert (tmp_path / ".architecture-models" / "docs" / "components" / "COMP-1.md").exists()
```

**Step 3: Run, verify, commit**

```bash
git add src/architecture_model/cli/main.py tests/test_docs_cli.py
git commit -m "feat: add 'architecture-model docs' CLI command"
```

---

### Task 8: Wire into Pipeline (auto-generation on model save)

**Files:**
- Modify: `src/architecture_model/orchestration/pipeline.py`

**Step 1: After save_model in from-scratch path, call generate_docs**

```python
# After line 261 (save_model) in from-scratch path:
try:
    from architecture_model.docs import generate_docs
    docs_dir = out / "docs"
    generate_docs(model, output_dir=docs_dir, manifest=flat_manifest)
    logger.info("  Generated architecture docs in %s", docs_dir)
except Exception as exc:
    logger.debug("Doc generation skipped: %s", exc)
```

Also after the enrichment save in the existing-model path:
```python
# After saving enriched model:
try:
    from architecture_model.docs import generate_docs
    docs_dir = (project_root / ".architecture-models" / "docs")
    generate_docs(_enrichment_model, output_dir=docs_dir, manifest=_flat_manifest)
    logger.info("  Generated architecture docs")
except Exception as exc:
    logger.debug("Doc generation skipped: %s", exc)
```

**Step 2: Run full suite, verify, commit**

```bash
git add src/architecture_model/orchestration/pipeline.py
git commit -m "feat: auto-generate docs on pipeline run"
```

---

### Task 9: Integration test — run on Flask

**Step 1: Run on Flask benchmark repo**

```bash
/opt/anaconda3/bin/python -c "
from pathlib import Path
from architecture_model.core.parser import load_model
from architecture_model.docs import generate_docs
from architecture_model.manifest.generator import generate_manifest

root = Path('/tmp/arch-bench/flask')
model = load_model(root / '.architecture-model.yaml')
manifest = generate_manifest(root)
result = generate_docs(model, output_dir=root / '.architecture-models' / 'docs', manifest=manifest)
for k, v in result.items():
    print(f'{k}: {len(v)} files')
"
```

**Step 2: Inspect generated docs**

Read `README.md`, one component spec, the health report, and the dependency matrix. Verify they contain meaningful content from the real Flask model.

**Step 3: Final commit if any fixes needed**

---

## Execution Notes

- Tasks 1-6 are independent doc generators — could be parallelized
- Task 7 (CLI) depends on tasks 1-6
- Task 8 (pipeline wiring) depends on task 7
- Task 9 (integration) depends on all

- Existing `visualize.py` already generates Mermaid — Task 1 just calls it
- Existing `differ.py` already computes diffs — Task 5 just formats the output
- All generators are pure functions (model → string) — easy to test deterministically
