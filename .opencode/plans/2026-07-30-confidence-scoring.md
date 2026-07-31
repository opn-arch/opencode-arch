# Confidence Scoring — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add per-entity confidence scores to the architecture model, measuring how well we understand each component/behavior/capability/interface — computed as a heuristic of field completeness weighted toward regeneration ability, auto-computed on load/validate, with a CLI visualization command and calibration via actual regeneration testing.

**Architecture:** `confidence: float` field on `BaseEntity` (inherited by all). A `compute_confidence()` function scores each entity based on weighted field completeness. Auto-triggered on `validate_model()` and `load_model()`. CLI command in opencode-arch shows confidence heatmap per block. Calibration command picks high-confidence components and tests regeneration.

**Tech Stack:** Python 3.12, dataclasses, pytest. Both repos.

**Test commands:**
- arch-std: `/opt/anaconda3/bin/pytest tests/ -v --ignore=tests/test_config_loader.py`
- opencode-arch: `/opt/anaconda3/bin/pytest tests/ -v`

---

### Task 1: Add `confidence` field to BaseEntity

**Files:**
- Modify: `src/architecture_model/core/types.py` (`BaseEntity` class)
- Test: `tests/test_confidence_field.py`

**Step 1: Write the failing test**

```python
"""Test confidence field on entities."""
from architecture_model.core.types import Component, Behavior, Capability, Interface, Status, Priority


def test_component_has_confidence_default_zero():
    c = Component(id="C1", name="Test", status=Status.ACTIVE)
    assert c.confidence == 0.0


def test_behavior_has_confidence():
    b = Behavior(id="B1", name="Test", status=Status.ACTIVE)
    assert b.confidence == 0.0


def test_capability_has_confidence():
    cap = Capability(id="CAP-1", name="Test", status=Status.ACTIVE)
    assert cap.confidence == 0.0


def test_interface_has_confidence():
    i = Interface(id="IF-1", name="Test", status=Status.ACTIVE)
    assert i.confidence == 0.0


def test_confidence_set_explicitly():
    c = Component(id="C1", name="Test", status=Status.ACTIVE, confidence=0.85)
    assert c.confidence == 0.85


def test_confidence_roundtrip_yaml():
    from architecture_model.core.parser import load_model
    import tempfile
    from pathlib import Path

    model_yaml = """\
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Test
      status: ACTIVE
      confidence: 0.92
relationships: []
"""
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        f.write(model_yaml)
        f.flush()
        model = load_model(Path(f.name))
    assert model.entities.components[0].confidence == 0.92
```

**Step 2:** Run → FAIL

**Step 3:** Add to `BaseEntity` (after `extensions` field):
```python
    confidence: float = 0.0
```

**Step 4:** Run → PASS

**Step 5:** Full suite

**Step 6:** Commit:
```bash
git add src/architecture_model/core/types.py tests/test_confidence_field.py
git commit -m "feat: add confidence field to BaseEntity (inherited by all entity types)"
```

---

### Task 2: Confidence computation engine

**Files:**
- Create: `src/architecture_model/core/confidence.py`
- Test: `tests/test_confidence_engine.py`

**Step 1: Write the failing test**

```python
"""Test confidence computation engine."""
from architecture_model.core.confidence import (
    compute_component_confidence,
    compute_behavior_confidence,
    compute_capability_confidence,
    compute_interface_confidence,
    compute_model_confidence,
)
from architecture_model.core.types import (
    Component, Behavior, Capability, Interface, Status, Priority,
    FunctionSignature, Symbol, TestContract, ArchitectureModel, Meta, Entities,
    Relationship,
)


def test_empty_component_zero_confidence():
    c = Component(id="C1", name="Empty", status=Status.ACTIVE)
    score = compute_component_confidence(c)
    assert score == 0.0


def test_full_component_high_confidence():
    c = Component(
        id="C1", name="Full", status=Status.ACTIVE,
        contract="Handles MQTT fan entities",
        pattern="entity-platform",
        signatures=[FunctionSignature(name="setup", params=["hass"], returns="None")],
        symbols=[Symbol(name="MqttFan", members=["turn_on", "turn_off"])],
        test_contracts=[TestContract(test_file="test_fan.py", test_method="test_on", assertion="state=on")],
        responsibilities=["Handle fan commands"],
        files=["mqtt/fan.py"],
    )
    score = compute_component_confidence(c)
    assert score >= 0.9


def test_partial_component_medium_confidence():
    c = Component(
        id="C1", name="Partial", status=Status.ACTIVE,
        contract="Handles something",
        files=["a.py"],
    )
    score = compute_component_confidence(c)
    assert 0.2 < score < 0.6


def test_empty_behavior_zero():
    b = Behavior(id="B1", name="Empty", status=Status.ACTIVE)
    score = compute_behavior_confidence(b)
    assert score == 0.0


def test_full_behavior_high():
    b = Behavior(
        id="B1", name="Full", status=Status.ACTIVE,
        trigger="MQTT message received",
        actor="MQTTClient",
        steps=["Parse payload", "Update entity state", "Fire event"],
        preconditions=["Connected to broker"],
        postconditions=["Entity state updated"],
    )
    score = compute_behavior_confidence(b)
    assert score >= 0.85


def test_capability_with_requirements():
    cap = Capability(id="CAP-1", name="Cap", status=Status.ACTIVE,
                     description="Handles MQTT", requirements=["Must support QoS 1"])
    score = compute_capability_confidence(cap)
    assert score >= 0.6


def test_capability_realized_boosts_score():
    """Capability realized by a component gets bonus."""
    cap = Capability(id="CAP-1", name="Cap", status=Status.ACTIVE,
                     description="Handles MQTT", requirements=["QoS 1"])
    # Without realization context
    base_score = compute_capability_confidence(cap)
    # With realization
    boosted = compute_capability_confidence(cap, realized=True)
    assert boosted > base_score


def test_interface_full():
    i = Interface(id="IF-1", name="MQTT API", status=Status.ACTIVE,
                  protocol="MQTT", data_format="JSON",
                  provider="COMP-1", consumer="COMP-2",
                  endpoints=[{"topic": "home/fan"}], schema="mqtt_schema.json")
    score = compute_interface_confidence(i)
    assert score >= 0.9


def test_compute_model_confidence_fills_all():
    """compute_model_confidence sets confidence on every entity."""
    model = ArchitectureModel(
        meta=Meta(project="test", schema_version="1.3"),
        entities=Entities(
            components=[
                Component(id="C1", name="A", status=Status.ACTIVE, contract="Does X", files=["a.py"]),
                Component(id="C2", name="B", status=Status.ACTIVE),
            ],
            behaviors=[Behavior(id="B1", name="Flow", status=Status.ACTIVE, steps=["a", "b"])],
        ),
        relationships=[Relationship(source="C1", target="CAP-1", type="realizes")],
    )
    updated = compute_model_confidence(model)
    assert updated.entities.components[0].confidence > 0
    assert updated.entities.components[1].confidence == 0.0
    assert updated.entities.behaviors[0].confidence > 0
```

**Step 2:** Run → FAIL

**Step 3:** Create `src/architecture_model/core/confidence.py`:

```python
"""Confidence scoring engine for architecture entities.

Computes a 0.0–1.0 confidence score per entity based on weighted field
completeness. Higher confidence = higher likelihood we could regenerate
the entity's implementation from the model alone.

Weights are tuned toward regeneration:
- Contract (what it does) is most important
- Signatures (how to call it) enable code generation
- Test contracts (expected behavior) verify correctness
- Pattern (structural template) guides implementation shape
"""
from __future__ import annotations

from architecture_model.core.types import (
    ArchitectureModel,
    Behavior,
    Capability,
    Component,
    Interface,
)


def compute_component_confidence(comp: Component) -> float:
    """Compute confidence for a Component. Returns 0.0–1.0."""
    score = 0.0

    # Contract (25%) — most important for regeneration
    if comp.contract:
        score += 0.25

    # Signatures (20%) — need to know the API
    if comp.signatures:
        # Bonus for signatures with return types
        has_returns = any(s.returns for s in comp.signatures)
        score += 0.20 if has_returns else 0.15

    # Pattern (15%) — structural template
    if comp.pattern:
        score += 0.15

    # Test contracts (15%) — verifiable behavior
    if comp.test_contracts:
        score += 0.15

    # Symbols (10%) — class structure
    if comp.symbols:
        has_members = any(s.members for s in comp.symbols)
        score += 0.10 if has_members else 0.07

    # Constants (5%)
    if comp.constants:
        score += 0.05

    # Responsibilities (5%)
    if comp.responsibilities:
        score += 0.05

    # Files mapped (5%)
    if comp.files:
        score += 0.05

    return min(score, 1.0)


def compute_behavior_confidence(behavior: Behavior) -> float:
    """Compute confidence for a Behavior. Returns 0.0–1.0."""
    score = 0.0

    # Steps (30%) — the actual flow
    if behavior.steps:
        score += 0.30 if len(behavior.steps) >= 2 else 0.15

    # Preconditions (15%)
    if behavior.preconditions:
        score += 0.15

    # Postconditions (15%)
    if behavior.postconditions:
        score += 0.15

    # Trigger (15%)
    if behavior.trigger:
        score += 0.15

    # States (15%) — for state machines
    if behavior.states:
        score += 0.15

    # Actor (10%)
    if behavior.actor:
        score += 0.10

    return min(score, 1.0)


def compute_capability_confidence(capability: Capability, *, realized: bool = False) -> float:
    """Compute confidence for a Capability. Returns 0.0–1.0."""
    score = 0.0

    # Requirements (40%)
    if capability.requirements:
        score += 0.40

    # Description (30%)
    if capability.description:
        score += 0.30

    # Realized by component (30%)
    if realized:
        score += 0.30

    return min(score, 1.0)


def compute_interface_confidence(interface: Interface) -> float:
    """Compute confidence for an Interface. Returns 0.0–1.0."""
    score = 0.0

    # Protocol (20%)
    if interface.protocol:
        score += 0.20

    # Endpoints (25%)
    if interface.endpoints:
        score += 0.25

    # Schema (20%)
    if interface.schema:
        score += 0.20

    # Provider + Consumer linked (20%)
    if interface.provider and interface.consumer:
        score += 0.20
    elif interface.provider or interface.consumer:
        score += 0.10

    # Data format (15%)
    if interface.data_format:
        score += 0.15

    return min(score, 1.0)


def compute_model_confidence(model: ArchitectureModel) -> ArchitectureModel:
    """Compute and set confidence on all entities in the model.

    Also checks relationships to determine if capabilities are realized.
    Returns the model with confidence fields populated.
    """
    # Find realized capabilities
    realized_caps = set()
    for rel in model.relationships:
        if rel.type == "realizes":
            realized_caps.add(rel.target)

    # Components
    for comp in model.entities.components:
        comp.confidence = compute_component_confidence(comp)

    # Behaviors
    for beh in model.entities.behaviors:
        beh.confidence = compute_behavior_confidence(beh)

    # Capabilities
    for cap in model.entities.capabilities:
        cap.confidence = compute_capability_confidence(cap, realized=cap.id in realized_caps)

    # Interfaces
    for iface in model.entities.interfaces:
        iface.confidence = compute_interface_confidence(iface)

    return model
```

**Step 4:** Run → PASS

**Step 5:** Full suite

**Step 6:** Commit:
```bash
git add src/architecture_model/core/confidence.py tests/test_confidence_engine.py
git commit -m "feat: confidence computation engine with per-entity scoring"
```

---

### Task 3: Auto-compute confidence on validate and load

**Files:**
- Modify: `src/architecture_model/core/validator.py`
- Modify: `src/architecture_model/core/parser.py`
- Test: `tests/test_confidence_auto.py`

**Step 1: Write the failing test**

```python
"""Test that confidence is auto-computed on validate and load."""
import tempfile
from pathlib import Path

from architecture_model.core.types import (
    ArchitectureModel, Meta, Entities, Component, Status, FunctionSignature,
)
from architecture_model.core.validator import validate_model
from architecture_model.core.parser import load_model


def test_validate_sets_confidence():
    model = ArchitectureModel(
        meta=Meta(project="test", schema_version="1.3"),
        entities=Entities(components=[
            Component(id="C1", name="A", status=Status.ACTIVE,
                      contract="Does X", pattern="adapter",
                      signatures=[FunctionSignature(name="run", params=["x"], returns="str")],
                      files=["a.py"]),
        ]),
        relationships=[],
    )
    assert model.entities.components[0].confidence == 0.0
    validate_model(model)
    assert model.entities.components[0].confidence > 0.5


def test_load_model_sets_confidence():
    model_yaml = """\
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: C1
      name: A
      status: ACTIVE
      contract: Does X
      files: [a.py]
relationships: []
"""
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        f.write(model_yaml)
        f.flush()
        model = load_model(Path(f.name))
    assert model.entities.components[0].confidence > 0.0
```

**Step 2:** Run → FAIL (confidence stays 0)

**Step 3:** 

In `validator.py`, add at the end of `validate_model()` (before return):
```python
    from architecture_model.core.confidence import compute_model_confidence
    compute_model_confidence(model)
```

In `parser.py`, add at the end of `load_model()` (before return):
```python
    from architecture_model.core.confidence import compute_model_confidence
    compute_model_confidence(model)
```

**Step 4:** Run → PASS

**Step 5:** Full suite (ensure no regressions — confidence being set shouldn't break assertions about 0.0 defaults)

**Step 6:** Commit:
```bash
git add src/architecture_model/core/validator.py src/architecture_model/core/parser.py tests/test_confidence_auto.py
git commit -m "feat: auto-compute confidence on model load and validate"
```

---

### Task 4: Manifest-level function confidence (from ModuleInfo)

**Files:**
- Modify: `src/architecture_model/core/confidence.py`
- Test: `tests/test_confidence_manifest.py`

**Step 1: Write the failing test**

```python
"""Test manifest-based function confidence scoring."""
from architecture_model.core.confidence import compute_function_confidence
from architecture_model.manifest.types import FunctionInfo


def test_empty_function_low_confidence():
    fi = FunctionInfo(name="foo", signature="()", calls=[], docstring=None, raises=[])
    score = compute_function_confidence(fi)
    assert score < 0.3


def test_documented_function_medium():
    fi = FunctionInfo(name="foo", signature="(x: int, y: str) -> bool",
                      calls=["validate", "process"], docstring="Does the thing.", raises=[])
    score = compute_function_confidence(fi)
    assert 0.5 <= score <= 0.8


def test_full_function_high():
    fi = FunctionInfo(name="foo", signature="(x: int, y: str) -> bool",
                      calls=["validate", "process"], docstring="Validates and processes input.",
                      raises=["ValueError", "TypeError"])
    score = compute_function_confidence(fi)
    assert score >= 0.8


def test_no_params_lower():
    fi = FunctionInfo(name="foo", signature="()", calls=[], docstring="Does stuff.", raises=[])
    score = compute_function_confidence(fi)
    fi2 = FunctionInfo(name="bar", signature="(x: int) -> str", calls=[], docstring="Does stuff.", raises=[])
    score2 = compute_function_confidence(fi2)
    assert score2 > score
```

**Step 2:** Run → FAIL

**Step 3:** Add to `confidence.py`:

```python
def compute_function_confidence(func_info) -> float:
    """Compute confidence for a function from manifest FunctionInfo.

    Factors:
    - Has typed signature (params with types, return type): 30%
    - Has docstring: 25%
    - Has call graph (calls list): 20%
    - Has raises info: 15%
    - Has parameters at all: 10%
    """
    score = 0.0
    sig = func_info.signature or ""

    # Typed signature (30%)
    has_return_type = "->" in sig
    has_typed_params = ":" in sig.split("->")[0] if sig else False
    if has_return_type and has_typed_params:
        score += 0.30
    elif has_return_type or has_typed_params:
        score += 0.15

    # Docstring (25%)
    if func_info.docstring:
        score += 0.25

    # Call graph (20%)
    if func_info.calls:
        score += 0.20 if len(func_info.calls) >= 2 else 0.10

    # Raises (15%)
    if func_info.raises:
        score += 0.15

    # Has parameters (10%)
    # Check if signature has anything between parens other than empty
    inner = sig.split("(")[1].split(")")[0].strip() if "(" in sig else ""
    if inner and inner != "self":
        score += 0.10

    return min(score, 1.0)
```

**Step 4:** Run → PASS

**Step 5:** Full suite

**Step 6:** Commit:
```bash
git add src/architecture_model/core/confidence.py tests/test_confidence_manifest.py
git commit -m "feat: function-level confidence scoring from manifest FunctionInfo"
```

---

### Task 5: Aggregate confidence per block + model summary

**Files:**
- Modify: `src/architecture_model/core/confidence.py`
- Test: `tests/test_confidence_aggregate.py`

**Step 1: Write the failing test**

```python
"""Test confidence aggregation."""
from architecture_model.core.confidence import (
    compute_model_confidence,
    aggregate_block_confidence,
    model_confidence_summary,
)
from architecture_model.core.types import (
    ArchitectureModel, Meta, Entities, Component, Behavior, Status,
)


def test_aggregate_block_confidence():
    model = ArchitectureModel(
        meta=Meta(project="t", schema_version="1.3"),
        entities=Entities(components=[
            Component(id="C1", name="A", status=Status.ACTIVE, f_block="F1", contract="X", files=["a.py"]),
            Component(id="C2", name="B", status=Status.ACTIVE, f_block="F1"),
            Component(id="C3", name="C", status=Status.ACTIVE, f_block="F2", contract="Y", pattern="adapter", files=["c.py"]),
        ]),
        relationships=[],
    )
    compute_model_confidence(model)
    blocks = aggregate_block_confidence(model)
    assert "F1" in blocks
    assert "F2" in blocks
    assert blocks["F1"]["avg_confidence"] < blocks["F2"]["avg_confidence"]
    assert blocks["F1"]["entity_count"] == 2
    assert blocks["F2"]["entity_count"] == 1


def test_model_confidence_summary():
    model = ArchitectureModel(
        meta=Meta(project="t", schema_version="1.3"),
        entities=Entities(components=[
            Component(id="C1", name="A", status=Status.ACTIVE, contract="X", files=["a.py"]),
            Component(id="C2", name="B", status=Status.ACTIVE),
        ]),
        relationships=[],
    )
    compute_model_confidence(model)
    summary = model_confidence_summary(model)
    assert "overall" in summary
    assert "high_confidence" in summary  # count of entities >= 0.8
    assert "low_confidence" in summary   # count of entities < 0.3
    assert "gaps" in summary             # list of entities with lowest confidence
    assert summary["total_entities"] == 2
```

**Step 2:** Run → FAIL

**Step 3:** Add to `confidence.py`:

```python
def aggregate_block_confidence(model: ArchitectureModel) -> dict[str, dict]:
    """Aggregate confidence scores per F-block.

    Returns: {block_id: {avg_confidence, min_confidence, max_confidence, entity_count, gaps}}
    """
    from collections import defaultdict

    blocks: dict[str, list[float]] = defaultdict(list)

    for comp in model.entities.components:
        block = comp.f_block or "unassigned"
        blocks[block].append(comp.confidence)

    for beh in model.entities.behaviors:
        # Try to associate with f_block via tags or just "behaviors"
        blocks["behaviors"].append(beh.confidence)

    result = {}
    for block_id, scores in blocks.items():
        if not scores:
            continue
        result[block_id] = {
            "avg_confidence": sum(scores) / len(scores),
            "min_confidence": min(scores),
            "max_confidence": max(scores),
            "entity_count": len(scores),
        }
    return result


def model_confidence_summary(model: ArchitectureModel) -> dict:
    """Generate overall confidence summary for the model.

    Returns: {overall, high_confidence, low_confidence, total_entities, gaps}
    """
    all_scores = []
    gaps = []

    for comp in model.entities.components:
        all_scores.append((comp.id, comp.name, comp.confidence))
    for beh in model.entities.behaviors:
        all_scores.append((beh.id, beh.name, beh.confidence))
    for cap in model.entities.capabilities:
        all_scores.append((cap.id, cap.name, cap.confidence))
    for iface in model.entities.interfaces:
        all_scores.append((iface.id, iface.name, iface.confidence))

    if not all_scores:
        return {"overall": 0.0, "high_confidence": 0, "low_confidence": 0, "total_entities": 0, "gaps": []}

    scores_only = [s[2] for s in all_scores]
    high = sum(1 for s in scores_only if s >= 0.8)
    low = sum(1 for s in scores_only if s < 0.3)

    # Gaps: entities with lowest confidence
    sorted_entities = sorted(all_scores, key=lambda x: x[2])
    gaps = [{"id": e[0], "name": e[1], "confidence": e[2]} for e in sorted_entities[:5]]

    return {
        "overall": sum(scores_only) / len(scores_only),
        "high_confidence": high,
        "low_confidence": low,
        "total_entities": len(all_scores),
        "gaps": gaps,
    }
```

**Step 4:** Run → PASS

**Step 5:** Full suite

**Step 6:** Commit:
```bash
git add src/architecture_model/core/confidence.py tests/test_confidence_aggregate.py
git commit -m "feat: confidence aggregation per block and model summary"
```

---

### Task 6: CLI confidence command (opencode-arch)

**Files:**
- Create: `src/opencode_arch/cli/confidence.py`
- Modify: `src/opencode_arch/cli/main.py`
- Test: `tests/test_cli_confidence.py`

**Step 1: Write the failing test**

```python
"""Test CLI confidence command."""
import tempfile
from pathlib import Path
from unittest.mock import patch
from opencode_arch.cli.confidence import run_confidence


def test_run_confidence_with_model(tmp_path):
    model_yaml = """\
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: C1
      name: FullComp
      status: ACTIVE
      contract: Does X
      pattern: adapter
      files: [a.py]
      f_block: F1
    - id: C2
      name: EmptyComp
      status: ACTIVE
      f_block: F1
relationships: []
"""
    (tmp_path / ".architecture-model.yaml").write_text(model_yaml)
    output = run_confidence(str(tmp_path))
    assert "F1" in output
    assert "FullComp" in output or "C1" in output
    assert "confidence" in output.lower() or "%" in output


def test_run_confidence_no_model(tmp_path):
    output = run_confidence(str(tmp_path))
    assert "no model" in output.lower() or "not found" in output.lower()
```

**Step 2:** Run → FAIL

**Step 3:** Create `src/opencode_arch/cli/confidence.py`:

```python
"""CLI confidence visualization command.

Shows per-block confidence heatmap with gaps highlighted.
"""
from __future__ import annotations

from pathlib import Path


def run_confidence(repo_path: str) -> str:
    """Run confidence analysis and return formatted output."""
    root = Path(repo_path)
    model_file = root / ".architecture-model.yaml"
    if not model_file.exists():
        model_file = root / ".architecture-model-extracted.yaml"
    if not model_file.exists():
        return "Error: No model found. Run extraction first."

    try:
        from architecture_model.core.parser import load_model
        from architecture_model.core.confidence import (
            compute_model_confidence,
            aggregate_block_confidence,
            model_confidence_summary,
        )

        model = load_model(model_file)
        compute_model_confidence(model)
        blocks = aggregate_block_confidence(model)
        summary = model_confidence_summary(model)
    except Exception as e:
        return f"Error computing confidence: {e}"

    lines = []
    lines.append(f"# Confidence Report: {model.meta.project}")
    lines.append(f"Overall: {summary['overall']:.0%} | "
                 f"High (≥80%): {summary['high_confidence']} | "
                 f"Low (<30%): {summary['low_confidence']} | "
                 f"Total: {summary['total_entities']}")
    lines.append("")

    # Per-block table
    lines.append(f"{'Block':<12} {'Avg':>6} {'Min':>6} {'Max':>6} {'Count':>6}")
    lines.append("-" * 42)
    for block_id in sorted(blocks.keys()):
        b = blocks[block_id]
        lines.append(f"{block_id:<12} {b['avg_confidence']:>5.0%} {b['min_confidence']:>5.0%} {b['max_confidence']:>5.0%} {b['entity_count']:>6}")

    lines.append("")

    # Gaps (lowest confidence entities)
    if summary["gaps"]:
        lines.append("## Top Gaps (lowest confidence)")
        for gap in summary["gaps"]:
            lines.append(f"  {gap['id']:<12} {gap['name']:<25} {gap['confidence']:.0%}")

    # Per-entity detail
    lines.append("")
    lines.append("## Entity Detail")
    for comp in model.entities.components:
        # Determine what's missing
        missing = []
        if not comp.contract:
            missing.append("contract")
        if not comp.pattern:
            missing.append("pattern")
        if not comp.signatures:
            missing.append("signatures")
        if not comp.test_contracts:
            missing.append("tests")
        gaps_str = ", ".join(missing) if missing else "-"
        lines.append(f"  {comp.id:<12} {comp.name:<25} {comp.confidence:>5.0%}  gaps: {gaps_str}")

    return "\n".join(lines)
```

**Step 4:** Register in `main.py` — add a `confidence` subcommand that calls `run_confidence` and prints the result.

**Step 5:** Run tests → PASS

**Step 6:** Full suite

**Step 7:** Commit:
```bash
git add src/opencode_arch/cli/confidence.py src/opencode_arch/cli/main.py tests/test_cli_confidence.py
git commit -m "feat: CLI confidence command with heatmap and gap analysis"
```

---

### Task 7: Calibration command (regeneration spot-check)

**Files:**
- Create: `src/opencode_arch/cli/calibrate.py`
- Modify: `src/opencode_arch/cli/main.py`
- Test: `tests/test_cli_calibrate.py`

**Step 1: Write the failing test**

```python
"""Test CLI calibrate command."""
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock

from opencode_arch.cli.calibrate import select_calibration_targets, format_calibration_prompt


def test_select_calibration_targets(tmp_path):
    model_yaml = """\
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: C1
      name: HighConf
      status: ACTIVE
      contract: Does X
      pattern: adapter
      files: [a.py]
      confidence: 0.9
    - id: C2
      name: LowConf
      status: ACTIVE
      confidence: 0.2
    - id: C3
      name: MedConf
      status: ACTIVE
      contract: Does Y
      confidence: 0.6
relationships: []
"""
    (tmp_path / ".architecture-model.yaml").write_text(model_yaml)
    from architecture_model.core.parser import load_model
    model = load_model(tmp_path / ".architecture-model.yaml")
    targets = select_calibration_targets(model, n=2, min_confidence=0.5)
    # Should pick high-confidence components only
    assert all(t.confidence >= 0.5 for t in targets)
    assert len(targets) <= 2


def test_format_calibration_prompt():
    from architecture_model.core.types import Component, Status, FunctionSignature
    comp = Component(
        id="C1", name="MqttFan", status=Status.ACTIVE,
        contract="Exposes MQTT fans as HA fan entities",
        pattern="entity-platform",
        signatures=[FunctionSignature(name="async_setup_entry", params=["hass", "config_entry"], returns="None")],
        files=["mqtt/fan.py"],
    )
    prompt = format_calibration_prompt(comp)
    assert "MqttFan" in prompt
    assert "entity-platform" in prompt
    assert "async_setup_entry" in prompt
    assert "regenerate" in prompt.lower() or "implement" in prompt.lower()
```

**Step 2:** Run → FAIL

**Step 3:** Create `src/opencode_arch/cli/calibrate.py`:

```python
"""Calibration command — spot-check confidence by attempting regeneration.

Picks N high-confidence components, asks the agent to regenerate them
from the model alone, then compares to the actual source to validate
that confidence scores correlate with regeneration success.
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from architecture_model.core.types import ArchitectureModel, Component


def select_calibration_targets(
    model: ArchitectureModel, *, n: int = 3, min_confidence: float = 0.7
) -> list[Component]:
    """Select N components with confidence >= min_confidence for calibration."""
    candidates = [c for c in model.entities.components if c.confidence >= min_confidence and c.files]
    if not candidates:
        # Fall back to any components with files
        candidates = [c for c in model.entities.components if c.files]
    random.shuffle(candidates)
    return candidates[:n]


def format_calibration_prompt(comp: Component) -> str:
    """Format a prompt asking the agent to regenerate a component from its model spec.

    The agent should implement the component using ONLY the information provided
    (contract, pattern, signatures, symbols, etc.) — NO reading source files.
    """
    sections = []
    sections.append(f"## Regenerate: {comp.name} ({comp.id})")
    sections.append("")
    sections.append(f"**Contract:** {comp.contract or 'Not specified'}")
    sections.append(f"**Pattern:** {comp.pattern or 'Not specified'}")
    sections.append(f"**Files:** {', '.join(comp.files)}")

    if comp.responsibilities:
        sections.append(f"**Responsibilities:** {'; '.join(comp.responsibilities)}")

    if comp.signatures:
        sections.append("\n**Signatures:**")
        for sig in comp.signatures:
            params = ", ".join(sig.params) if sig.params else ""
            ret = f" -> {sig.returns}" if sig.returns else ""
            decorators = " ".join(f"@{d}" for d in sig.decorators) + " " if sig.decorators else ""
            sections.append(f"  {decorators}def {sig.name}({params}){ret}")
            if sig.body_hint:
                sections.append(f"    # Hint: {sig.body_hint}")

    if comp.symbols:
        sections.append("\n**Classes:**")
        for sym in comp.symbols:
            bases = f"({', '.join(sym.supers)})" if sym.supers else ""
            sections.append(f"  class {sym.name}{bases}")
            if sym.members:
                for m in sym.members[:10]:
                    sections.append(f"    - {m}")

    if comp.constants:
        sections.append("\n**Constants:**")
        for const in comp.constants:
            sections.append(f"  {const.name} = {const.value}")

    if comp.test_contracts:
        sections.append("\n**Expected behavior (from tests):**")
        for tc in comp.test_contracts[:5]:
            sections.append(f"  {tc.test_method}: {tc.assertion}")

    sections.append("\n---")
    sections.append("**Task:** Implement this component using ONLY the specification above.")
    sections.append("Do NOT read source files. Generate the complete implementation.")

    return "\n".join(sections)


def compare_regeneration(original_path: Path, generated_code: str) -> dict[str, Any]:
    """Compare generated code against original source.

    Returns metrics about how well regeneration matched:
    - function_match: % of functions present in both
    - class_match: % of classes present in both
    - line_ratio: generated/original line count ratio
    """
    import ast

    original_code = original_path.read_text()

    def extract_names(code: str) -> tuple[set[str], set[str]]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return set(), set()
        functions = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        classes = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
        return functions, classes

    orig_funcs, orig_classes = extract_names(original_code)
    gen_funcs, gen_classes = extract_names(generated_code)

    func_match = len(orig_funcs & gen_funcs) / len(orig_funcs) if orig_funcs else 1.0
    class_match = len(orig_classes & gen_classes) / len(orig_classes) if orig_classes else 1.0
    line_ratio = len(generated_code.splitlines()) / max(1, len(original_code.splitlines()))

    return {
        "function_match": func_match,
        "class_match": class_match,
        "line_ratio": line_ratio,
        "original_functions": len(orig_funcs),
        "generated_functions": len(gen_funcs),
        "calibration_score": (func_match * 0.5 + class_match * 0.3 + min(line_ratio, 1.0) * 0.2),
    }
```

**Step 4:** Run tests → PASS

**Step 5:** Register in `main.py` as `calibrate` subcommand

**Step 6:** Full suite

**Step 7:** Commit:
```bash
git add src/opencode_arch/cli/calibrate.py src/opencode_arch/cli/main.py tests/test_cli_calibrate.py
git commit -m "feat: calibration command for regeneration spot-checking"
```

---

### Task 8: Export confidence APIs + integrate with monitoring

**Files:**
- Modify: `src/architecture_model/__init__.py`
- Modify: `src/architecture_model/core/confidence.py` (add @monitored)
- Test: verify imports

**Step 1:** Add exports to `src/architecture_model/__init__.py`:
```python
from architecture_model.core.confidence import (
    compute_component_confidence,
    compute_behavior_confidence,
    compute_capability_confidence,
    compute_interface_confidence,
    compute_function_confidence,
    compute_model_confidence,
    aggregate_block_confidence,
    model_confidence_summary,
)
```

**Step 2:** Add `@monitored` to `compute_model_confidence`:
```python
@monitored(
    module="core.confidence",
    outputs=lambda r: {"total_entities": len(r.entities.components) + len(r.entities.behaviors)},
)
def compute_model_confidence(model):
```

**Step 3:** Verify + full suite

**Step 4:** Commit:
```bash
git add src/architecture_model/__init__.py src/architecture_model/core/confidence.py
git commit -m "feat: export confidence APIs and add monitoring"
```

---

## Summary

| Task | Repo | What | New Tests |
|------|------|------|-----------|
| 1 | arch-std | `confidence` field on BaseEntity | 6 |
| 2 | arch-std | Confidence computation engine (per-entity scoring) | 9 |
| 3 | arch-std | Auto-compute on validate/load | 2 |
| 4 | arch-std | Function-level confidence from manifest | 4 |
| 5 | arch-std | Aggregate per-block + model summary | 2 |
| 6 | opencode-arch | CLI `confidence` command (heatmap + gaps) | 2 |
| 7 | opencode-arch | CLI `calibrate` command (regeneration spot-check) | 2 |
| 8 | arch-std | Export APIs + monitoring integration | 0 |

**Total new tests: 27**
**Estimated time: 45-60 minutes**

### What This Enables

After implementation, running `opencode-arch confidence /path/to/repo` shows:
```
# Confidence Report: homeassistant
Overall: 52% | High (≥80%): 3 | Low (<30%): 4 | Total: 13

Block        Avg    Min    Max  Count
------------------------------------------
F1             65%    40%    90%      3
F6             72%    55%    95%      4
F8             35%    20%    50%      3

## Top Gaps (lowest confidence)
  C7           HueDiscovery              20%
  C8           AuthStore                 25%
  C11          HelperUtils               28%

## Entity Detail
  C1           MQTTClient                90%  gaps: tests
  C2           MqttFan                   95%  gaps: -
  C3           MqttDiscovery             55%  gaps: pattern, signatures, tests
```

And `opencode-arch calibrate /path/to/repo` picks high-confidence components and verifies the model is rich enough for regeneration.
