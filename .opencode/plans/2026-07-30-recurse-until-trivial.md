# Recurse Until Trivial — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make decomposition recurse until every leaf cluster is 1-3 files, add pattern/contract fields to Component, create a starter pattern catalog, and build an enrichment context formatter for single-pass agent annotation.

**Architecture:** Pipeline-driven iteration — `run_pipeline` calls `deep_decompose_block` repeatedly on sub-clusters that exceed the leaf threshold (3 files). Pattern catalog is YAML package data. Component gains `pattern` and `contract` string fields directly.

**Tech Stack:** Python 3.12, dataclasses, PyYAML, pytest. Target repo: `architecture-model-standard`.

**Test command:** `pytest tests/ -v --ignore=tests/test_config_loader.py`

---

### Task 1: Add `pattern` and `contract` fields to Component

**Files:**
- Modify: `src/architecture_model/core/types.py` (Component class, ~line 417)
- Test: `tests/test_pattern_contract_fields.py`

**Step 1: Write the failing test**

```python
"""Test pattern and contract fields on Component."""
from architecture_model.core.types import Component, Status


def test_component_has_pattern_field():
    c = Component(id="COMP-1", name="Test", status=Status.ACTIVE)
    assert c.pattern == ""
    c2 = Component(id="COMP-2", name="Test2", status=Status.ACTIVE, pattern="entity-platform")
    assert c2.pattern == "entity-platform"


def test_component_has_contract_field():
    c = Component(id="COMP-1", name="Test", status=Status.ACTIVE)
    assert c.contract == ""
    c2 = Component(id="COMP-2", name="Test2", status=Status.ACTIVE, contract="Translates MQTT messages to HA entity state updates")
    assert c2.contract == "Translates MQTT messages to HA entity state updates"


def test_pattern_contract_roundtrip_yaml():
    """Pattern and contract survive YAML serialization."""
    from architecture_model.core.parser import load_model
    import yaml, tempfile
    from pathlib import Path

    model_yaml = """\
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: MQTTFan
      status: ACTIVE
      pattern: entity-platform
      contract: Exposes MQTT fan devices as HA fan entities
relationships: []
"""
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        f.write(model_yaml)
        f.flush()
        model = load_model(Path(f.name))
    assert model.entities.components[0].pattern == "entity-platform"
    assert model.entities.components[0].contract == "Exposes MQTT fan devices as HA fan entities"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_pattern_contract_fields.py -v`
Expected: FAIL — `TypeError: unexpected keyword argument 'pattern'`

**Step 3: Write minimal implementation**

In `src/architecture_model/core/types.py`, add to Component class (after `region` field):

```python
    pattern: str = ""
    contract: str = ""
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_pattern_contract_fields.py -v`
Expected: PASS (3 tests)

**Step 5: Run full suite**

Run: `pytest tests/ -v --ignore=tests/test_config_loader.py`
Expected: All pass (no regressions)

**Step 6: Commit**

```bash
git add src/architecture_model/core/types.py tests/test_pattern_contract_fields.py
git commit -m "feat: add pattern and contract fields to Component"
```

---

### Task 2: Create starter pattern catalog

**Files:**
- Create: `src/architecture_model/data/patterns.yaml`
- Create: `src/architecture_model/data/__init__.py`
- Create: `src/architecture_model/patterns.py` (loader)
- Test: `tests/test_patterns_catalog.py`

**Step 1: Write the failing test**

```python
"""Test pattern catalog loading."""
from architecture_model.patterns import load_patterns, get_pattern


def test_load_patterns_returns_dict():
    patterns = load_patterns()
    assert isinstance(patterns, dict)
    assert len(patterns) >= 10


def test_pattern_has_required_fields():
    patterns = load_patterns()
    for name, p in patterns.items():
        assert "description" in p, f"{name} missing description"
        assert "indicators" in p, f"{name} missing indicators"
        assert isinstance(p["indicators"], list)


def test_get_pattern_returns_none_for_unknown():
    assert get_pattern("nonexistent-xyz") is None


def test_get_pattern_returns_dict_for_known():
    p = get_pattern("entity-platform")
    assert p is not None
    assert "description" in p
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_patterns_catalog.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'architecture_model.patterns'`

**Step 3: Create the pattern catalog YAML**

File: `src/architecture_model/data/patterns.yaml`

```yaml
# Architecture Pattern Catalog
# Each pattern represents a recognizable 1-3 file structural unit

entity-platform:
  description: "Platform adapter exposing domain devices as HA entities"
  indicators:
    - "class *Entity"
    - "async_setup_entry"
    - "PLATFORM_SCHEMA"
  typical_files: 1-2
  contract_template: "Exposes {domain} devices as HA {entity_type} entities"

config-flow:
  description: "Multi-step user configuration wizard"
  indicators:
    - "class *FlowHandler(ConfigFlow)"
    - "async_step_user"
    - "async_step_confirm"
  typical_files: 1
  contract_template: "Guides user through {integration} setup via UI steps"

event-handler:
  description: "Subscribes to events and dispatches actions"
  indicators:
    - "async_track_"
    - "@callback"
    - "hass.bus.async_listen"
  typical_files: 1
  contract_template: "Reacts to {event_type} events by {action}"

data-class:
  description: "Pure data container with validation"
  indicators:
    - "@dataclass"
    - "TypedDict"
    - "NamedTuple"
  typical_files: 1
  contract_template: "Holds {domain} data with {validation_type} validation"

adapter:
  description: "Translates between two interfaces/protocols"
  indicators:
    - "client"
    - "async_connect"
    - "parse_"
    - "serialize_"
  typical_files: 1-2
  contract_template: "Translates between {source_protocol} and {target_protocol}"

repository:
  description: "Persistence layer abstracting storage"
  indicators:
    - "async_save"
    - "async_load"
    - "Store"
    - "async_get"
  typical_files: 1
  contract_template: "Persists {entity} data to {storage_backend}"

state-machine:
  description: "Manages explicit state transitions"
  indicators:
    - "STATE_"
    - "transition"
    - "_state"
    - "async_set_state"
  typical_files: 1-2
  contract_template: "Manages {entity} lifecycle through states: {state_list}"

registry:
  description: "Central lookup/registration for typed entries"
  indicators:
    - "register"
    - "_registry"
    - "async_get_"
    - "DATA_"
  typical_files: 1
  contract_template: "Registers and resolves {entry_type} by {key_type}"

message-transformer:
  description: "Parses, validates, and transforms messages"
  indicators:
    - "payload"
    - "decode"
    - "encode"
    - "schema"
  typical_files: 1
  contract_template: "Transforms {input_format} messages into {output_format}"

reconnecting-client:
  description: "Network client with automatic reconnection"
  indicators:
    - "async_connect"
    - "reconnect"
    - "_disconnect"
    - "backoff"
  typical_files: 1-2
  contract_template: "Maintains persistent connection to {service} with auto-reconnect"
```

**Step 4: Create the loader module**

File: `src/architecture_model/patterns.py`

```python
"""Pattern catalog loader."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_CATALOG_PATH = Path(__file__).parent / "data" / "patterns.yaml"
_cache: dict[str, Any] | None = None


def load_patterns() -> dict[str, Any]:
    """Load the pattern catalog. Cached after first call."""
    global _cache
    if _cache is None:
        with open(_CATALOG_PATH) as f:
            _cache = yaml.safe_load(f)
    return _cache


def get_pattern(name: str) -> dict[str, Any] | None:
    """Get a single pattern by name, or None if not found."""
    return load_patterns().get(name)
```

File: `src/architecture_model/data/__init__.py` — empty file.

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_patterns_catalog.py -v`
Expected: PASS (4 tests)

**Step 6: Run full suite**

Run: `pytest tests/ -v --ignore=tests/test_config_loader.py`

**Step 7: Commit**

```bash
git add src/architecture_model/data/ src/architecture_model/patterns.py tests/test_patterns_catalog.py
git commit -m "feat: add starter pattern catalog (10 patterns)"
```

---

### Task 3: Iterative deep decomposition (recurse until trivial)

**Files:**
- Modify: `src/architecture_model/orchestration/deep_decompose.py`
- Modify: `src/architecture_model/orchestration/pipeline.py`
- Test: `tests/test_recursive_decompose.py`

**Step 1: Write the failing test**

```python
"""Test iterative deep decomposition until leaf threshold."""
from architecture_model.orchestration.deep_decompose import (
    deep_decompose_block,
    iterative_decompose,
    DecomposeResult,
)
from architecture_model.manifest.types import Manifest, ModuleInfo


def _make_manifest(n_modules: int) -> Manifest:
    """Create a manifest with n modules that import each other sequentially."""
    modules = {}
    for i in range(n_modules):
        name = f"mod_{i}"
        imports = [f"mod_{i-1}"] if i > 0 else []
        modules[name] = ModuleInfo(
            path=f"pkg/mod_{i}.py",
            classes=[],
            functions=[f"func_{i}"],
            imports=imports,
            lines=50,
            status="OK",
        )
    return Manifest(
        root="pkg",
        modules=modules,
        generated_at="2026-01-01T00:00:00",
        meta={},
    )


def test_iterative_decompose_reaches_leaf_size():
    """With 30 modules and leaf_max=3, all leaves should have <= 3 files."""
    manifest = _make_manifest(30)
    results = iterative_decompose(
        manifest, block_id="F1", block_name="Test", leaf_max_files=3
    )
    assert len(results) >= 1
    # Check all leaf sub-components
    for r in results:
        for sc in r.sub_components:
            assert len(sc.files) <= 3, f"{sc.id} has {len(sc.files)} files"


def test_iterative_decompose_small_block_returns_empty():
    """A 3-file block is already a leaf — no decomposition needed."""
    manifest = _make_manifest(3)
    results = iterative_decompose(
        manifest, block_id="F1", block_name="Test", leaf_max_files=3
    )
    assert results == []


def test_iterative_decompose_depth_tracked():
    """Each iteration increases depth."""
    manifest = _make_manifest(20)
    results = iterative_decompose(
        manifest, block_id="F1", block_name="Test", leaf_max_files=3
    )
    if results:
        depths = [r.depth for r in results]
        assert max(depths) >= 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_recursive_decompose.py -v`
Expected: FAIL — `ImportError: cannot import name 'iterative_decompose'`

**Step 3: Implement iterative_decompose**

Add to `src/architecture_model/orchestration/deep_decompose.py`:

```python
def iterative_decompose(
    manifest: Manifest,
    *,
    block_id: str,
    block_name: str,
    leaf_max_files: int = 3,
    max_depth: int = 5,
    target_k: int = 4,
    min_cluster_size: int = 2,
) -> list[DecomposeResult]:
    """Iteratively decompose until all clusters are <= leaf_max_files.

    Uses pipeline-driven iteration: decompose, check sizes, re-decompose
    clusters that are still too large.

    Returns list of DecomposeResult objects (one per decomposition round
    that produced sub-components). Empty list if block is already a leaf.
    """
    results: list[DecomposeResult] = []

    # Queue: (modules_subset, parent_id, depth)
    queue: list[tuple[list[str], str, int]] = [
        (list(manifest.modules.keys()), block_id, 0)
    ]

    while queue:
        modules, parent_id, depth = queue.pop(0)

        if len(modules) <= leaf_max_files or depth >= max_depth:
            continue

        # Build sub-manifest for this subset
        sub_modules = {m: manifest.modules[m] for m in modules if m in manifest.modules}
        sub_manifest = Manifest(
            root=manifest.root,
            modules=sub_modules,
            generated_at=manifest.generated_at,
            meta=manifest.meta,
        )

        decomp = deep_decompose_block(
            sub_manifest,
            block_id=parent_id,
            block_name=block_name,
            max_modules=leaf_max_files,
            target_k=target_k,
            min_cluster_size=min_cluster_size,
            parent_id=parent_id,
        )
        decomp.depth = depth + 1

        if decomp.sub_components:
            results.append(decomp)
            # Queue sub-components that are still too large
            for sc in decomp.sub_components:
                if len(sc.files) > leaf_max_files:
                    queue.append((sc.files, sc.id, depth + 1))

    return results
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_recursive_decompose.py -v`
Expected: PASS (3 tests)

**Step 5: Update pipeline to use iterative_decompose**

In `src/architecture_model/orchestration/pipeline.py`, replace lines 81-90:

```python
    if deep:
        from architecture_model.orchestration.deep_decompose import iterative_decompose
        logger.info("Step 1.5: Iterative deep decomposition...")
        for block_id, rm in manifests.items():
            decomps = iterative_decompose(
                rm.manifest, block_id=block_id, block_name=rm.block_name
            )
            if decomps:
                # Store the final (deepest) decomposition for each block
                result.deep_decompositions[block_id] = decomps[-1]
                total_leaves = sum(len(d.sub_components) for d in decomps)
                logger.info("  %s: %d rounds, %d total sub-components",
                           block_id, len(decomps), total_leaves)
```

**Step 6: Run full suite**

Run: `pytest tests/ -v --ignore=tests/test_config_loader.py`
Expected: All pass

**Step 7: Commit**

```bash
git add src/architecture_model/orchestration/deep_decompose.py src/architecture_model/orchestration/pipeline.py tests/test_recursive_decompose.py
git commit -m "feat: iterative decomposition until all clusters <= leaf_max_files"
```

---

### Task 4: Enrichment context formatter

**Files:**
- Create: `src/architecture_model/orchestration/enrichment_context.py`
- Test: `tests/test_enrichment_context.py`

**Step 1: Write the failing test**

```python
"""Test enrichment context formatter for agent annotation."""
from architecture_model.orchestration.enrichment_context import format_enrichment_prompt
from architecture_model.orchestration.deep_decompose import DecomposeResult, SubComponent, InternalRelationship


def _sample_tree() -> list[DecomposeResult]:
    return [DecomposeResult(
        block_id="F6",
        block_name="MQTT",
        sub_components=[
            SubComponent(id="COMP-F6-1", name="", files=["mqtt/client.py", "mqtt/connection.py"], classes=["MQTTClient"], functions=["async_connect"], line_count=200),
            SubComponent(id="COMP-F6-2", name="", files=["mqtt/fan.py"], classes=["MqttFan"], functions=["async_setup_entry"], line_count=80),
            SubComponent(id="COMP-F6-3", name="", files=["mqtt/light.py"], classes=["MqttLight"], functions=["async_setup_entry"], line_count=90),
        ],
        internal_relationships=[
            InternalRelationship(from_id="COMP-F6-2", to_id="COMP-F6-1", edge_count=3),
            InternalRelationship(from_id="COMP-F6-3", to_id="COMP-F6-1", edge_count=2),
        ],
        depth=1,
    )]


def test_format_enrichment_prompt_contains_all_leaves():
    prompt = format_enrichment_prompt(_sample_tree())
    assert "COMP-F6-1" in prompt
    assert "COMP-F6-2" in prompt
    assert "COMP-F6-3" in prompt


def test_format_enrichment_prompt_includes_pattern_catalog():
    prompt = format_enrichment_prompt(_sample_tree())
    assert "entity-platform" in prompt
    assert "reconnecting-client" in prompt


def test_format_enrichment_prompt_includes_instructions():
    prompt = format_enrichment_prompt(_sample_tree())
    assert "pattern" in prompt.lower()
    assert "contract" in prompt.lower()


def test_format_enrichment_prompt_compact():
    """Should be under 2000 tokens (~8000 chars) for 3 leaves."""
    prompt = format_enrichment_prompt(_sample_tree())
    assert len(prompt) < 8000
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_enrichment_context.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement enrichment context formatter**

File: `src/architecture_model/orchestration/enrichment_context.py`

```python
"""Format enrichment context for single-pass agent annotation.

Given a tree of decomposition results, produces a compact prompt
that lets the agent classify every leaf with a pattern + one-sentence contract.
"""
from __future__ import annotations

from architecture_model.orchestration.deep_decompose import DecomposeResult
from architecture_model.patterns import load_patterns


def format_enrichment_prompt(decompositions: list[DecomposeResult]) -> str:
    """Format all leaves for agent pattern/contract annotation.

    Returns a prompt string containing:
    1. Available patterns with indicators
    2. All leaf components with their files/classes/functions
    3. Instructions for annotation format
    """
    sections: list[str] = []

    # Section 1: Pattern catalog (compact)
    patterns = load_patterns()
    sections.append("## Available Patterns\n")
    for name, p in patterns.items():
        indicators = ", ".join(p["indicators"][:3])
        sections.append(f"- **{name}**: {p['description']} [{indicators}]")

    sections.append("")

    # Section 2: Leaves to annotate
    sections.append("## Components to Annotate\n")
    for decomp in decompositions:
        sections.append(f"### {decomp.block_name} ({decomp.block_id})\n")
        for sc in decomp.sub_components:
            files_str = ", ".join(sc.files[:5])
            if len(sc.files) > 5:
                files_str += f" +{len(sc.files) - 5} more"
            classes_str = ", ".join(sc.classes[:4]) if sc.classes else "-"
            funcs_str = ", ".join(sc.functions[:4]) if sc.functions else "-"
            sections.append(
                f"**{sc.id}** ({sc.line_count} lines)\n"
                f"  Files: {files_str}\n"
                f"  Classes: {classes_str}\n"
                f"  Functions: {funcs_str}\n"
            )

    # Section 3: Instructions
    sections.append("## Instructions\n")
    sections.append(
        "For each component above, respond with YAML:\n"
        "```yaml\n"
        "- id: COMP-XX-N\n"
        "  pattern: <pattern-name or 'custom'>\n"
        "  contract: <one sentence: what it does, for whom, how>\n"
        "```\n\n"
        "Rules:\n"
        "- Contract must be ONE sentence (no 'and' joining two responsibilities)\n"
        "- If no pattern fits, use 'custom' and the contract still applies\n"
        "- Use indicators + file/class names to infer pattern\n"
    )

    return "\n".join(sections)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_enrichment_context.py -v`
Expected: PASS (4 tests)

**Step 5: Run full suite**

Run: `pytest tests/ -v --ignore=tests/test_config_loader.py`

**Step 6: Commit**

```bash
git add src/architecture_model/orchestration/enrichment_context.py tests/test_enrichment_context.py
git commit -m "feat: enrichment context formatter for agent annotation"
```

---

### Task 5: Integration test — full pipeline with enrichment

**Files:**
- Test: `tests/test_full_enrichment_flow.py`

**Step 1: Write the integration test**

```python
"""Integration test: pipeline -> iterative decompose -> enrichment prompt."""
import tempfile
from pathlib import Path

from architecture_model.orchestration.pipeline import run_pipeline
from architecture_model.orchestration.enrichment_context import format_enrichment_prompt


def test_full_flow_synthetic_repo(tmp_path):
    """Create a synthetic repo, run pipeline with deep=True, produce enrichment prompt."""
    # Create 20 Python files in a package
    pkg = tmp_path / "myapp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")

    for i in range(20):
        code = f"import myapp.mod_{max(0,i-1)}\nclass Handler{i}:\n    def process(self): pass\n"
        (pkg / f"mod_{i}.py").write_text(code)

    # Write config with one F-block covering all files
    config = tmp_path / ".architecture-model.yaml"
    config.write_text("""\
meta:
  project: test-enrichment
  schema_version: '1.3'
functional_blocks:
  F1:
    name: MyApp
    dirs:
      - myapp
entities:
  components: []
relationships: []
""")

    result = run_pipeline(tmp_path, deep=True)
    assert "F1" in result.manifests
    assert len(result.deep_decompositions) > 0

    # Generate enrichment prompt from decompositions
    prompt = format_enrichment_prompt(list(result.deep_decompositions.values()))
    assert "COMP-" in prompt
    assert "pattern" in prompt.lower()
    assert len(prompt) < 20000  # reasonable size
```

**Step 2: Run test**

Run: `pytest tests/test_full_enrichment_flow.py -v`
Expected: PASS

**Step 3: Run full suite**

Run: `pytest tests/ -v --ignore=tests/test_config_loader.py`

**Step 4: Commit**

```bash
git add tests/test_full_enrichment_flow.py
git commit -m "test: integration test for full enrichment flow"
```

---

### Task 6: Export new APIs from package

**Files:**
- Modify: `src/architecture_model/__init__.py`
- Modify: `src/architecture_model/orchestration/__init__.py`

**Step 1: Add exports**

In `src/architecture_model/__init__.py`, add:
```python
from architecture_model.patterns import load_patterns, get_pattern
from architecture_model.orchestration.enrichment_context import format_enrichment_prompt
```

In `src/architecture_model/orchestration/__init__.py`, add:
```python
from architecture_model.orchestration.deep_decompose import iterative_decompose
from architecture_model.orchestration.enrichment_context import format_enrichment_prompt
```

**Step 2: Verify imports work**

Run: `python -c "from architecture_model import load_patterns, get_pattern, format_enrichment_prompt; print('OK')"`
Expected: `OK`

**Step 3: Run full suite**

Run: `pytest tests/ -v --ignore=tests/test_config_loader.py`

**Step 4: Commit**

```bash
git add src/architecture_model/__init__.py src/architecture_model/orchestration/__init__.py
git commit -m "feat: export pattern catalog and enrichment APIs"
```

---

## Summary

| Task | What | New Tests |
|------|------|-----------|
| 1 | `pattern` + `contract` fields on Component | 3 |
| 2 | Pattern catalog (10 patterns in YAML) | 4 |
| 3 | `iterative_decompose()` — recurse until leaf | 3 |
| 4 | Enrichment context formatter | 4 |
| 5 | Integration test (full flow) | 1 |
| 6 | Package exports | 0 |

**Total new tests: 15**
**Estimated time: 30-45 minutes**

After this plan completes, the next step is the **proof-of-value**: enrich HA Core F6 (MQTT) using the enrichment prompt, then demonstrate that a task ("add MQTT vacuum entity platform") can be specified from the model alone.
