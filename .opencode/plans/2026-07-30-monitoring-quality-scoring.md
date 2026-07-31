# Monitoring & Automated Quality Scoring — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add per-function monitoring with automated quality scoring to architecture-model-standard (returns metrics) and opencode-arch (collects and stores them), enabling data-driven optimization of the extraction pipeline.

**Architecture:** Two-layer design. `architecture-model-standard` gets a `@monitored` decorator that wraps functions, collecting timing + input/output metrics + quality indicators into a `FunctionMetrics` dataclass. Functions return their normal result — metrics are accumulated in a thread-local collector. `opencode-arch` drains the collector after each MCP tool call and writes to a new `function_metrics` table in telemetry.db.

**Tech Stack:** Python 3.12, dataclasses, time.perf_counter, threading.local, SQLite, pytest.

**Test commands:**
- arch-std: `pytest tests/ -v --ignore=tests/test_config_loader.py` (use `/opt/anaconda3/bin/pytest`)
- opencode-arch: `pytest tests/ -v`

---

### Task 1: FunctionMetrics dataclass + collector (architecture-model-standard)

**Files:**
- Create: `src/architecture_model/monitoring.py`
- Test: `tests/test_monitoring.py`

**Step 1: Write the failing test**

```python
"""Test monitoring infrastructure."""
import time
from architecture_model.monitoring import (
    FunctionMetrics,
    MetricsCollector,
    get_collector,
    monitored,
)


def test_function_metrics_dataclass():
    m = FunctionMetrics(
        function="test_fn",
        module="test_module",
        time_ms=42.5,
        quality_scores={"score": 95},
        input_metrics={"count": 10},
        output_metrics={"size": 200},
    )
    assert m.function == "test_fn"
    assert m.time_ms == 42.5
    assert m.quality_scores["score"] == 95


def test_collector_accumulates_metrics():
    collector = MetricsCollector()
    m1 = FunctionMetrics(function="fn1", module="mod", time_ms=10.0)
    m2 = FunctionMetrics(function="fn2", module="mod", time_ms=20.0)
    collector.record(m1)
    collector.record(m2)
    assert len(collector.metrics) == 2
    drained = collector.drain()
    assert len(drained) == 2
    assert len(collector.metrics) == 0


def test_get_collector_returns_thread_local():
    c1 = get_collector()
    c2 = get_collector()
    assert c1 is c2


def test_monitored_decorator_records_timing():
    collector = get_collector()
    collector.drain()  # clear

    @monitored(module="test")
    def slow_fn(x):
        time.sleep(0.01)
        return x * 2

    result = slow_fn(5)
    assert result == 10
    metrics = collector.drain()
    assert len(metrics) == 1
    assert metrics[0].function == "slow_fn"
    assert metrics[0].time_ms >= 9  # at least 9ms


def test_monitored_with_quality_extractor():
    collector = get_collector()
    collector.drain()

    @monitored(module="test", quality=lambda result: {"leaf_count": len(result)})
    def get_items():
        return [1, 2, 3]

    result = get_items()
    assert result == [1, 2, 3]
    metrics = collector.drain()
    assert metrics[0].quality_scores == {"leaf_count": 3}


def test_monitored_with_input_extractor():
    collector = get_collector()
    collector.drain()

    @monitored(module="test", inputs=lambda args, kwargs: {"n": args[0]})
    def square(n):
        return n * n

    assert square(4) == 16
    metrics = collector.drain()
    assert metrics[0].input_metrics == {"n": 4}
```

**Step 2:** Run: `/opt/anaconda3/bin/pytest tests/test_monitoring.py -v` → FAIL

**Step 3: Implement**

```python
"""Per-function monitoring infrastructure.

Provides a @monitored decorator that collects timing, input/output metrics,
and quality scores into a thread-local collector. The collector is drained
by the caller (e.g., opencode-arch MCP tools) after each operation.

Usage:
    from architecture_model.monitoring import monitored, get_collector

    @monitored(module="orchestration.pipeline",
               quality=lambda r: {"blocks": len(r.manifests)},
               inputs=lambda a, kw: {"deep": kw.get("deep", False)})
    def run_pipeline(project_root, *, deep=False):
        ...

    # After calling:
    metrics = get_collector().drain()
"""
from __future__ import annotations

import functools
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class FunctionMetrics:
    """Metrics collected from a single function invocation."""
    function: str
    module: str
    time_ms: float = 0.0
    quality_scores: dict[str, Any] = field(default_factory=dict)
    input_metrics: dict[str, Any] = field(default_factory=dict)
    output_metrics: dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Thread-safe accumulator for function metrics."""

    def __init__(self):
        self.metrics: list[FunctionMetrics] = []
        self._lock = threading.Lock()

    def record(self, m: FunctionMetrics) -> None:
        with self._lock:
            self.metrics.append(m)

    def drain(self) -> list[FunctionMetrics]:
        """Return all collected metrics and clear the buffer."""
        with self._lock:
            result = self.metrics[:]
            self.metrics.clear()
            return result


_thread_local = threading.local()


def get_collector() -> MetricsCollector:
    """Get the thread-local metrics collector."""
    if not hasattr(_thread_local, "collector"):
        _thread_local.collector = MetricsCollector()
    return _thread_local.collector


def monitored(
    module: str,
    *,
    quality: Callable[[Any], dict[str, Any]] | None = None,
    inputs: Callable[[tuple, dict], dict[str, Any]] | None = None,
    outputs: Callable[[Any], dict[str, Any]] | None = None,
) -> Callable:
    """Decorator that records function metrics to the thread-local collector.

    Args:
        module: Dotted module path (e.g., "orchestration.pipeline")
        quality: Extracts quality scores from the return value
        inputs: Extracts input metrics from (args, kwargs)
        outputs: Extracts output metrics from the return value
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            input_m = {}
            if inputs:
                try:
                    input_m = inputs(args, kwargs)
                except Exception:
                    pass

            start = time.perf_counter()
            result = fn(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000

            quality_m = {}
            if quality:
                try:
                    quality_m = quality(result)
                except Exception:
                    pass

            output_m = {}
            if outputs:
                try:
                    output_m = outputs(result)
                except Exception:
                    pass

            m = FunctionMetrics(
                function=fn.__name__,
                module=module,
                time_ms=elapsed_ms,
                quality_scores=quality_m,
                input_metrics=input_m,
                output_metrics=output_m,
            )
            get_collector().record(m)
            return result

        return wrapper
    return decorator
```

**Step 4:** Run: `/opt/anaconda3/bin/pytest tests/test_monitoring.py -v` → PASS

**Step 5:** Run full suite: `/opt/anaconda3/bin/pytest tests/ -v --ignore=tests/test_config_loader.py`

**Step 6:** Commit:
```bash
git add src/architecture_model/monitoring.py tests/test_monitoring.py
git commit -m "feat: add monitoring infrastructure (FunctionMetrics + @monitored decorator)"
```

---

### Task 2: Apply @monitored to Tier 1 functions (architecture-model-standard)

**Files:**
- Modify: `src/architecture_model/orchestration/pipeline.py`
- Modify: `src/architecture_model/orchestration/deep_decompose.py`
- Modify: `src/architecture_model/manifest/generator.py`
- Modify: `src/architecture_model/manifest/recursive.py`
- Modify: `src/architecture_model/core/validator.py`
- Test: `tests/test_monitoring_tier1.py`

**Step 1: Write the failing test**

```python
"""Test that Tier 1 functions emit metrics."""
import tempfile
from pathlib import Path

from architecture_model.monitoring import get_collector


def test_generate_manifest_emits_metrics(tmp_path):
    collector = get_collector()
    collector.drain()

    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "mod.py").write_text("def hello(): pass\n")

    from architecture_model.manifest.generator import generate_manifest
    manifest = generate_manifest(tmp_path)

    metrics = collector.drain()
    fn_names = [m.function for m in metrics]
    assert "generate_manifest" in fn_names
    m = next(x for x in metrics if x.function == "generate_manifest")
    assert m.time_ms > 0
    assert "module_count" in m.output_metrics


def test_validate_model_emits_metrics():
    collector = get_collector()
    collector.drain()

    from architecture_model.core.types import ArchitectureModel, Meta, Entities
    from architecture_model.core.validator import validate_model

    model = ArchitectureModel(
        meta=Meta(project="test", schema_version="1.3"),
        entities=Entities(),
        relationships=[],
    )
    validate_model(model)

    metrics = collector.drain()
    fn_names = [m.function for m in metrics]
    assert "validate_model" in fn_names
    m = next(x for x in metrics if x.function == "validate_model")
    assert "score" in m.quality_scores


def test_run_pipeline_emits_metrics(tmp_path):
    collector = get_collector()
    collector.drain()

    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for i in range(5):
        (pkg / f"m{i}.py").write_text(f"def fn{i}(): pass\n")

    config = tmp_path / ".architecture-model.yaml"
    config.write_text("""
meta:
  project: test
  schema_version: '1.3'
functional_blocks:
  F1:
    name: App
    dirs:
      - app
entities:
  components: []
relationships: []
""")

    from architecture_model.orchestration.pipeline import run_pipeline
    run_pipeline(tmp_path)

    metrics = collector.drain()
    fn_names = [m.function for m in metrics]
    assert "run_pipeline" in fn_names
    assert "generate_recursive_manifests" in fn_names
```

**Step 2:** Run test → FAIL (functions don't emit metrics yet)

**Step 3:** Apply `@monitored` to each Tier 1 function. For each file, add the import and decorator:

In `src/architecture_model/manifest/generator.py`, wrap `generate_manifest`:
```python
from architecture_model.monitoring import monitored

@monitored(
    module="manifest.generator",
    outputs=lambda r: {"module_count": len(r.modules), "parse_failures": sum(1 for m in r.modules.values() if m.status != "OK")},
)
def generate_manifest(project_root: Path, config=None) -> Manifest:
    ...
```

In `src/architecture_model/manifest/recursive.py`, wrap `generate_recursive_manifests`:
```python
from architecture_model.monitoring import monitored

@monitored(
    module="manifest.recursive",
    outputs=lambda r: {"block_count": len(r), "total_modules": sum(len(rm.manifest.modules) for rm in r.values())},
)
def generate_recursive_manifests(...):
    ...
```

In `src/architecture_model/core/validator.py`, wrap `validate_model`:
```python
from architecture_model.monitoring import monitored

@monitored(
    module="core.validator",
    quality=lambda r: {"score": r.score, "issue_count": len(r.issues)},
    outputs=lambda r: {"entity_count": r.entity_count, "relationship_count": r.relationship_count},
)
def validate_model(model, strict=False):
    ...
```

In `src/architecture_model/orchestration/pipeline.py`, wrap `run_pipeline`:
```python
from architecture_model.monitoring import monitored

@monitored(
    module="orchestration.pipeline",
    inputs=lambda a, kw: {"deep": kw.get("deep", False)},
    outputs=lambda r: {"blocks_scanned": len(r.manifests), "blocks_decomposed": len(r.deep_decompositions), "errors": len(r.errors)},
)
def run_pipeline(...):
    ...
```

In `src/architecture_model/orchestration/deep_decompose.py`, wrap both functions:
```python
from architecture_model.monitoring import monitored

@monitored(
    module="orchestration.deep_decompose",
    outputs=lambda r: {"cluster_count": len(r.sub_components), "avg_cluster_size": (sum(len(sc.files) for sc in r.sub_components) / len(r.sub_components)) if r.sub_components else 0},
)
def deep_decompose_block(...):
    ...

@monitored(
    module="orchestration.deep_decompose",
    inputs=lambda a, kw: {"leaf_max_files": kw.get("leaf_max_files", 3)},
    outputs=lambda r: {"rounds": len(r), "total_sub_components": sum(len(d.sub_components) for d in r)},
    quality=lambda r: {"leaf_compliance_pct": 100.0 if not r else (sum(1 for d in r for sc in d.sub_components if len(sc.files) <= 3) / max(1, sum(len(d.sub_components) for d in r)) * 100)},
)
def iterative_decompose(...):
    ...
```

**Step 4:** Run: `/opt/anaconda3/bin/pytest tests/test_monitoring_tier1.py -v` → PASS

**Step 5:** Run full suite

**Step 6:** Commit:
```bash
git add src/architecture_model/orchestration/pipeline.py src/architecture_model/orchestration/deep_decompose.py src/architecture_model/manifest/generator.py src/architecture_model/manifest/recursive.py src/architecture_model/core/validator.py tests/test_monitoring_tier1.py
git commit -m "feat: apply @monitored to Tier 1 functions"
```

---

### Task 3: Apply @monitored to Tier 2 & 3 functions (architecture-model-standard)

**Files:**
- Modify: `src/architecture_model/core/cluster.py`
- Modify: `src/architecture_model/orchestration/enrichment_context.py`
- Modify: `src/architecture_model/orchestration/decompose.py`
- Modify: `src/architecture_model/core/coverage.py`
- Modify: `src/architecture_model/extract/from_code.py`
- Modify: `src/architecture_model/core/differ.py`
- Modify: `src/architecture_model/orchestration/enrich.py`
- Modify: `src/architecture_model/core/slicer.py`
- Test: `tests/test_monitoring_tier2.py`

**Step 1: Write the failing test**

```python
"""Test that Tier 2/3 functions emit metrics."""
from architecture_model.monitoring import get_collector


def test_cluster_modules_emits_metrics():
    collector = get_collector()
    collector.drain()

    from architecture_model.core.cluster import cluster_modules
    modules = ["a", "b", "c", "d", "e", "f"]
    edges = [("a", "b"), ("b", "c"), ("d", "e"), ("e", "f")]
    cluster_modules(modules, edges, target_k=2, min_cluster_size=2)

    metrics = collector.drain()
    fn_names = [m.function for m in metrics]
    assert "cluster_modules" in fn_names
    m = next(x for x in metrics if x.function == "cluster_modules")
    assert "cluster_count" in m.output_metrics
    assert "max_size" in m.output_metrics


def test_format_enrichment_prompt_emits_metrics():
    collector = get_collector()
    collector.drain()

    from architecture_model.orchestration.enrichment_context import format_enrichment_prompt
    from architecture_model.orchestration.deep_decompose import DecomposeResult, SubComponent

    decomps = [DecomposeResult(
        block_id="F1", block_name="Test",
        sub_components=[SubComponent(id="C1", name="", files=["a.py"], classes=[], functions=[], line_count=10)],
        internal_relationships=[], depth=1,
    )]
    format_enrichment_prompt(decomps)

    metrics = collector.drain()
    fn_names = [m.function for m in metrics]
    assert "format_enrichment_prompt" in fn_names
    m = next(x for x in metrics if x.function == "format_enrichment_prompt")
    assert "token_estimate" in m.output_metrics


def test_diff_models_emits_metrics():
    collector = get_collector()
    collector.drain()

    from architecture_model.core.types import ArchitectureModel, Meta, Entities
    from architecture_model.core.differ import diff_models

    model = ArchitectureModel(meta=Meta(project="t", schema_version="1.3"), entities=Entities(), relationships=[])
    diff_models(model, model)

    metrics = collector.drain()
    fn_names = [m.function for m in metrics]
    assert "diff_models" in fn_names
```

**Step 2:** Run test → FAIL

**Step 3:** Apply `@monitored` to each function:

`cluster.py`:
```python
@monitored(
    module="core.cluster",
    inputs=lambda a, kw: {"module_count": len(a[0]), "edge_count": len(a[1])},
    outputs=lambda r: {"cluster_count": len(r), "min_size": min(len(c) for c in r) if r else 0, "max_size": max(len(c) for c in r) if r else 0, "avg_size": sum(len(c) for c in r) / len(r) if r else 0},
)
def cluster_modules(...):
```

`enrichment_context.py`:
```python
@monitored(
    module="orchestration.enrichment_context",
    inputs=lambda a, kw: {"decomposition_count": len(a[0])},
    outputs=lambda r: {"token_estimate": len(r) // 4, "char_count": len(r)},
)
def format_enrichment_prompt(...):
```

`decompose.py` (orchestration):
```python
@monitored(
    module="orchestration.decompose",
    outputs=lambda r: {"sub_model_count": len(r)},
)
def decompose_model(...):
```

`coverage.py`:
```python
@monitored(
    module="core.coverage",
    quality=lambda r: {"component_coverage": r.component_coverage, "module_coverage": r.module_coverage},
    outputs=lambda r: {"unmapped_modules": len(r.unmapped_modules) if hasattr(r, 'unmapped_modules') else 0},
)
def coverage_report(...):
```

`extract/from_code.py`:
```python
@monitored(
    module="extract.from_code",
    outputs=lambda r: {"component_count": len(r.entities.components), "relationship_count": len(r.relationships)},
)
def extract_from_code(...):
```

`differ.py`:
```python
@monitored(
    module="core.differ",
    outputs=lambda r: {"added": len(r.added), "removed": len(r.removed), "modified": len(r.modified)},
)
def diff_models(...):
```

`enrich.py`:
```python
@monitored(
    module="orchestration.enrich",
    outputs=lambda r: {"component_count": len(r.entities.components)},
)
def enrich_model(...):
```

`slicer.py` — wrap all 4 slice functions:
```python
@monitored(
    module="core.slicer",
    outputs=lambda r: {"entities_retained": len(r.entities.components), "relationships_retained": len(r.relationships)},
)
def slice_by_fblock(...):

@monitored(module="core.slicer", outputs=lambda r: {"entities_retained": len(r.entities.components), "relationships_retained": len(r.relationships)})
def slice_by_layer(...):

@monitored(module="core.slicer", outputs=lambda r: {"entities_retained": len(r.entities.components), "relationships_retained": len(r.relationships)})
def slice_by_status(...):

@monitored(module="core.slicer", outputs=lambda r: {"entities_retained": len(r.entities.components), "relationships_retained": len(r.relationships)})
def slice_for_artifact(...):
```

`recursive.py` — add `compute_block_dependencies`:
```python
@monitored(
    module="manifest.recursive",
    outputs=lambda r: {"total_edges": sum(len(v) for v in r.values()), "block_count": len(r)},
)
def compute_block_dependencies(...):
```

**Step 4:** Run: `/opt/anaconda3/bin/pytest tests/test_monitoring_tier2.py -v` → PASS

**Step 5:** Full suite

**Step 6:** Commit:
```bash
git add src/architecture_model/core/cluster.py src/architecture_model/core/differ.py src/architecture_model/core/slicer.py src/architecture_model/core/coverage.py src/architecture_model/orchestration/enrichment_context.py src/architecture_model/orchestration/decompose.py src/architecture_model/orchestration/enrich.py src/architecture_model/extract/from_code.py src/architecture_model/manifest/recursive.py tests/test_monitoring_tier2.py
git commit -m "feat: apply @monitored to Tier 2 and 3 functions"
```

---

### Task 4: Export monitoring API (architecture-model-standard)

**Files:**
- Modify: `src/architecture_model/__init__.py`

**Step 1:** Add exports:
```python
from architecture_model.monitoring import FunctionMetrics, MetricsCollector, get_collector, monitored
```

**Step 2:** Verify: `python -c "from architecture_model import get_collector, FunctionMetrics; print('OK')"`

**Step 3:** Run full suite

**Step 4:** Commit:
```bash
git add src/architecture_model/__init__.py
git commit -m "feat: export monitoring API from package"
```

---

### Task 5: New `function_metrics` table in opencode-arch telemetry

**Files:**
- Modify: `src/opencode_arch/telemetry/store.py`
- Test: `tests/test_function_metrics_table.py`

**Step 1: Write the failing test**

```python
"""Test function_metrics table in telemetry store."""
import tempfile
from pathlib import Path
from opencode_arch.telemetry.store import TelemetryStore


def test_record_function_metrics(tmp_path):
    db = tmp_path / "test.db"
    store = TelemetryStore(str(db))
    store.record_function_metric(
        tool="architect_extract",
        function="validate_model",
        module="core.validator",
        repo="test-repo",
        time_ms=42.5,
        quality_scores='{"score": 95}',
        input_metrics='{"strict": false}',
        output_metrics='{"entity_count": 10}',
    )
    rows = store.get_function_metrics(repo="test-repo")
    assert len(rows) == 1
    assert rows[0]["function"] == "validate_model"
    assert rows[0]["time_ms"] == 42.5


def test_get_function_metrics_filtered(tmp_path):
    db = tmp_path / "test.db"
    store = TelemetryStore(str(db))
    store.record_function_metric(tool="scan", function="generate_manifest", module="manifest.generator", repo="r1", time_ms=10.0)
    store.record_function_metric(tool="extract", function="validate_model", module="core.validator", repo="r1", time_ms=20.0)
    store.record_function_metric(tool="scan", function="generate_manifest", module="manifest.generator", repo="r2", time_ms=30.0)

    r1 = store.get_function_metrics(repo="r1")
    assert len(r1) == 2

    scans = store.get_function_metrics(function="generate_manifest")
    assert len(scans) == 2

    by_tool = store.get_function_metrics(tool="scan")
    assert len(by_tool) == 2


def test_get_function_metrics_last_n(tmp_path):
    db = tmp_path / "test.db"
    store = TelemetryStore(str(db))
    for i in range(10):
        store.record_function_metric(tool="t", function=f"fn_{i}", module="m", repo="r", time_ms=float(i))

    last5 = store.get_function_metrics(last=5)
    assert len(last5) == 5
```

**Step 2:** Run test → FAIL

**Step 3:** Add to `TelemetryStore`:
- In `_init_db()`, add CREATE TABLE for `function_metrics`:
  ```sql
  CREATE TABLE IF NOT EXISTS function_metrics (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp REAL NOT NULL,
      tool TEXT NOT NULL,
      function TEXT NOT NULL,
      module TEXT NOT NULL DEFAULT '',
      repo TEXT DEFAULT '',
      time_ms REAL DEFAULT 0.0,
      quality_scores TEXT DEFAULT '{}',
      input_metrics TEXT DEFAULT '{}',
      output_metrics TEXT DEFAULT '{}'
  )
  ```
- Add method `record_function_metric(self, tool, function, module, repo="", time_ms=0.0, quality_scores="{}", input_metrics="{}", output_metrics="{}")`
- Add method `get_function_metrics(self, *, repo=None, function=None, tool=None, last=None) -> list[dict]`

**Step 4:** Run test → PASS

**Step 5:** Full suite: `pytest tests/ -v`

**Step 6:** Commit:
```bash
git add src/opencode_arch/telemetry/store.py tests/test_function_metrics_table.py
git commit -m "feat: add function_metrics table to telemetry store"
```

---

### Task 6: Collector integration in MCP tools (opencode-arch)

**Files:**
- Create: `src/opencode_arch/telemetry/collector.py`
- Modify: `src/opencode_arch/mcp/tools/scan.py`
- Modify: `src/opencode_arch/mcp/tools/slice.py`
- Modify: `src/opencode_arch/mcp/tools/validate.py`
- Modify: `src/opencode_arch/mcp/tools/extract.py`
- Modify: `src/opencode_arch/mcp/tools/generate.py`
- Test: `tests/test_collector_integration.py`

**Step 1: Write the failing test**

```python
"""Test that MCP tools drain metrics from arch-std and store them."""
import tempfile
from pathlib import Path
from unittest.mock import patch

from opencode_arch.telemetry.collector import drain_and_store


def test_drain_and_store_writes_to_telemetry(tmp_path):
    """Simulate metrics in collector, drain and store."""
    from architecture_model.monitoring import get_collector, FunctionMetrics

    collector = get_collector()
    collector.drain()  # clear

    # Simulate what a monitored function would do
    collector.record(FunctionMetrics(
        function="generate_manifest",
        module="manifest.generator",
        time_ms=55.0,
        quality_scores={},
        input_metrics={},
        output_metrics={"module_count": 15},
    ))
    collector.record(FunctionMetrics(
        function="validate_model",
        module="core.validator",
        time_ms=2.0,
        quality_scores={"score": 92},
        input_metrics={},
        output_metrics={},
    ))

    db_path = tmp_path / "test.db"
    count = drain_and_store(tool="architect_scan", repo="my-repo", db_path=str(db_path))
    assert count == 2

    from opencode_arch.telemetry.store import TelemetryStore
    store = TelemetryStore(str(db_path))
    rows = store.get_function_metrics(repo="my-repo")
    assert len(rows) == 2
    fns = [r["function"] for r in rows]
    assert "generate_manifest" in fns
    assert "validate_model" in fns
```

**Step 2:** Run test → FAIL

**Step 3:** Create `src/opencode_arch/telemetry/collector.py`:

```python
"""Drain metrics from architecture-model-standard and store in telemetry.

Call drain_and_store() at the end of each MCP tool invocation to persist
all function-level metrics that were collected during the operation.
"""
from __future__ import annotations

import json


def drain_and_store(tool: str, repo: str = "", db_path: str | None = None) -> int:
    """Drain the thread-local metrics collector and write to telemetry DB.

    Returns the number of metrics stored. Never raises — swallows all exceptions.
    """
    try:
        from architecture_model.monitoring import get_collector
        from opencode_arch.telemetry.store import TelemetryStore

        collector = get_collector()
        metrics = collector.drain()
        if not metrics:
            return 0

        store = TelemetryStore(db_path) if db_path else TelemetryStore()
        for m in metrics:
            store.record_function_metric(
                tool=tool,
                function=m.function,
                module=m.module,
                repo=repo,
                time_ms=m.time_ms,
                quality_scores=json.dumps(m.quality_scores),
                input_metrics=json.dumps(m.input_metrics),
                output_metrics=json.dumps(m.output_metrics),
            )
        return len(metrics)
    except Exception:
        return 0
```

**Step 4:** Add `drain_and_store` call at the end of each MCP tool function. Pattern for each tool:

```python
# At end of scan_repository(), slice_context(), validate_architecture(),
# store_extraction(), run_tests_on_generated_code():
from opencode_arch.telemetry.collector import drain_and_store
drain_and_store(tool="architect_scan", repo=repo_name)
```

Add this to each tool file, wrapping in try/except to never fail the tool.

**Step 5:** Run test → PASS

**Step 6:** Full suite: `pytest tests/ -v`

**Step 7:** Commit:
```bash
git add src/opencode_arch/telemetry/collector.py src/opencode_arch/mcp/tools/ tests/test_collector_integration.py
git commit -m "feat: drain arch-std metrics into telemetry after each MCP tool call"
```

---

### Task 7: Consistency checks (automated quality scoring)

**Files:**
- Create: `src/architecture_model/monitoring_checks.py`
- Test: `tests/test_monitoring_checks.py`

**Step 1: Write the failing test**

```python
"""Test automated consistency/quality checks."""
from architecture_model.monitoring_checks import (
    check_decompose_idempotency,
    check_cluster_stability,
    check_pattern_indicators,
    ConsistencyResult,
)
from architecture_model.manifest.types import Manifest, ModuleInfo


def _make_manifest(n: int) -> Manifest:
    modules = {}
    for i in range(n):
        modules[f"mod_{i}"] = ModuleInfo(
            path=f"pkg/mod_{i}.py", classes=[], functions=[f"fn_{i}"],
            imports=[f"mod_{i-1}"] if i > 0 else [], lines=50, status="OK",
        )
    return Manifest(root="pkg", modules=modules, generated_at="2026-01-01", meta={})


def test_decompose_idempotency_pass():
    manifest = _make_manifest(15)
    result = check_decompose_idempotency(manifest, block_id="F1", block_name="Test")
    assert isinstance(result, ConsistencyResult)
    assert result.passed is True
    assert result.metric_name == "decompose_idempotency"


def test_cluster_stability():
    modules = [f"m{i}" for i in range(10)]
    edges = [(f"m{i}", f"m{i+1}") for i in range(9)]
    result = check_cluster_stability(modules, edges)
    assert isinstance(result, ConsistencyResult)
    assert 0.0 <= result.score <= 1.0


def test_pattern_indicators_match():
    """Check that pattern indicators are found in file content."""
    file_contents = {"fan.py": "class MqttFan(MqttEntity):\n    async def async_setup_entry(hass):\n        pass\n"}
    result = check_pattern_indicators("entity-platform", file_contents)
    assert result.passed is True
    assert result.score > 0.5


def test_pattern_indicators_mismatch():
    file_contents = {"utils.py": "def helper(): pass\n"}
    result = check_pattern_indicators("entity-platform", file_contents)
    assert result.passed is False
    assert result.score < 0.5
```

**Step 2:** Run test → FAIL

**Step 3:** Implement:

```python
"""Automated consistency and quality checks for monitoring.

These checks provide automated quality scoring without an external oracle:
- Idempotency: same input → same output (decomposition stability)
- Stability: small perturbations → similar clusters
- Pattern matching: assigned patterns match actual code indicators
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ConsistencyResult:
    """Result of an automated consistency check."""
    metric_name: str
    passed: bool
    score: float  # 0.0 to 1.0
    details: dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


def check_decompose_idempotency(manifest, *, block_id: str, block_name: str, runs: int = 3) -> ConsistencyResult:
    """Run iterative_decompose multiple times, check outputs match."""
    from architecture_model.orchestration.deep_decompose import iterative_decompose

    results = []
    for _ in range(runs):
        r = iterative_decompose(manifest, block_id=block_id, block_name=block_name)
        # Extract cluster file sets for comparison
        clusters = []
        for decomp in r:
            for sc in decomp.sub_components:
                clusters.append(frozenset(sc.files))
        results.append(frozenset(clusters))

    # All runs should produce identical cluster sets
    unique = len(set(str(r) for r in results))
    passed = unique == 1
    return ConsistencyResult(
        metric_name="decompose_idempotency",
        passed=passed,
        score=1.0 if passed else 1.0 / unique,
        details={"runs": runs, "unique_outputs": unique},
    )


def check_cluster_stability(modules: list[str], edges: list[tuple[str, str]], perturbations: int = 5) -> ConsistencyResult:
    """Check that removing one edge doesn't drastically change clusters."""
    from architecture_model.core.cluster import cluster_modules
    import random

    if not edges:
        return ConsistencyResult(metric_name="cluster_stability", passed=True, score=1.0, details={"reason": "no edges"})

    base_clusters = cluster_modules(modules, edges, target_k=4, min_cluster_size=2)
    base_sets = [frozenset(c) for c in base_clusters]

    similarities = []
    rng = random.Random(42)  # deterministic
    for _ in range(min(perturbations, len(edges))):
        # Remove one random edge
        perturbed = edges[:]
        idx = rng.randint(0, len(perturbed) - 1)
        perturbed.pop(idx)
        new_clusters = cluster_modules(modules, perturbed, target_k=4, min_cluster_size=2)
        new_sets = [frozenset(c) for c in new_clusters]

        # Jaccard-like similarity: how many modules stay in same cluster?
        same_count = 0
        for m in modules:
            base_cluster = next((s for s in base_sets if m in s), None)
            new_cluster = next((s for s in new_sets if m in s), None)
            if base_cluster and new_cluster and base_cluster == new_cluster:
                same_count += 1
        similarities.append(same_count / len(modules) if modules else 1.0)

    avg_similarity = sum(similarities) / len(similarities) if similarities else 1.0
    return ConsistencyResult(
        metric_name="cluster_stability",
        passed=avg_similarity >= 0.7,
        score=avg_similarity,
        details={"perturbations": len(similarities), "avg_similarity": avg_similarity},
    )


def check_pattern_indicators(pattern_name: str, file_contents: dict[str, str]) -> ConsistencyResult:
    """Check if assigned pattern's indicators appear in file contents."""
    from architecture_model.patterns import get_pattern

    pattern = get_pattern(pattern_name)
    if not pattern:
        return ConsistencyResult(metric_name="pattern_indicators", passed=False, score=0.0, details={"error": f"unknown pattern: {pattern_name}"})

    indicators = pattern.get("indicators", [])
    if not indicators:
        return ConsistencyResult(metric_name="pattern_indicators", passed=True, score=1.0)

    all_content = "\n".join(file_contents.values())
    matched = 0
    for indicator in indicators:
        # Simple substring/glob match (strip leading/trailing *)
        search = indicator.strip("*").strip()
        if search in all_content:
            matched += 1

    score = matched / len(indicators) if indicators else 1.0
    return ConsistencyResult(
        metric_name="pattern_indicators",
        passed=score >= 0.3,  # at least 1/3 indicators found
        score=score,
        details={"indicators_total": len(indicators), "indicators_matched": matched},
    )
```

**Step 4:** Run test → PASS

**Step 5:** Full suite

**Step 6:** Commit:
```bash
git add src/architecture_model/monitoring_checks.py tests/test_monitoring_checks.py
git commit -m "feat: automated consistency checks (idempotency, stability, pattern matching)"
```

---

### Task 8: Export consistency checks + update CONTEXT.md references

**Files:**
- Modify: `src/architecture_model/__init__.py`

**Step 1:** Add:
```python
from architecture_model.monitoring_checks import (
    check_decompose_idempotency,
    check_cluster_stability,
    check_pattern_indicators,
    ConsistencyResult,
)
```

**Step 2:** Verify imports, run full suite

**Step 3:** Commit:
```bash
git add src/architecture_model/__init__.py
git commit -m "feat: export consistency check APIs"
```

---

## Summary

| Task | Repo | What | New Tests |
|------|------|------|-----------|
| 1 | arch-std | Monitoring infrastructure (@monitored + collector) | 6 |
| 2 | arch-std | @monitored on Tier 1 (pipeline, decompose, manifest, validate) | 3 |
| 3 | arch-std | @monitored on Tier 2/3 (cluster, enrichment, differ, slicer, etc.) | 3 |
| 4 | arch-std | Export monitoring API | 0 |
| 5 | opencode-arch | function_metrics table in telemetry.db | 3 |
| 6 | opencode-arch | Collector drains arch-std metrics into telemetry | 1 |
| 7 | arch-std | Automated consistency checks | 4 |
| 8 | arch-std | Export consistency APIs | 0 |

**Total new tests: 20**
**Estimated time: 45-60 minutes**
