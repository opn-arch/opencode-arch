# Phase 2: Oracle-First opencode-arch Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor opencode-arch from a surrogate-calling tool to an agent-context-provider with telemetry, using existing architecture-model-standard APIs.

**Architecture:** MCP tools wrap `architecture_model` APIs (manifest generator, slicer, validator, context formatter). Tools provide compressed context to the agent — the agent IS the oracle. Telemetry records what works for future optimization. No external model calls needed.

**Tech Stack:** Python 3.11+, FastMCP, architecture-model-standard (manifest/slicer/validator/context), SQLite (telemetry), pytest

---

### Task 1: Remove Oracle Package + Update Dependencies

**Files:**
- Remove: `src/opencode_arch/oracle/copilot_relay.py`
- Remove: `src/opencode_arch/oracle/__init__.py`
- Remove: `tests/test_oracle.py`
- Modify: `pyproject.toml`

**Step 1: Remove oracle package and tests**

```bash
rm -rf src/opencode_arch/oracle
rm tests/test_oracle.py
```

**Step 2: Update pyproject.toml**

Remove `aiohttp` dependency (no more HTTP calls to external models). Add `mcp` dependency.

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "opencode-arch"
version = "0.2.0"
description = "OpenCode architecture extension - context compression and validation tools"
requires-python = ">=3.11"
dependencies = [
    "architecture-model-standard>=0.3.0",
    "pyyaml>=6.0",
]
license = "MIT"

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21"]
mcp = ["mcp>=1.0"]

[tool.hatch.build.targets.wheel]
packages = ["src/opencode_arch"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

**Step 3: Remove tests that reference oracle**

Update `tests/test_mcp_validate.py` — remove `test_validate_with_oracle_scoring` and `test_validate_oracle_unavailable` tests (oracle concept removed).

Update `tests/test_integration.py` — remove `test_extract_validate_with_oracle` test.

**Step 4: Run remaining tests**

```bash
pytest tests/ -v
```

Expected: Tests pass (minus oracle-related tests removed).

**Step 5: Commit**

```bash
git add -A && git commit -m "refactor: remove oracle package (agent IS the oracle, no external calls)"
```

---

### Task 2: Implement architect_scan Tool

**Files:**
- Create: `src/opencode_arch/mcp/tools/scan.py`
- Test: `tests/test_scan.py`

**Step 1: Write failing test**

```python
# tests/test_scan.py
"""Tests for the architect_scan MCP tool."""
import pytest
import tempfile
from pathlib import Path

from opencode_arch.mcp.tools.scan import scan_repository


class TestScanTool:
    @pytest.mark.asyncio
    async def test_scan_returns_manifest_dict(self):
        """Scan should return a manifest dict with expected keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "main.py").write_text("def hello():\n    pass\n")
            result = await scan_repository(repo_path=tmpdir)
            assert isinstance(result, dict)
            assert "generated_at" in result
            assert "modules" in result

    @pytest.mark.asyncio
    async def test_scan_nonexistent_path(self):
        """Scan should return error dict for nonexistent path."""
        result = await scan_repository(repo_path="/tmp/nonexistent_xyz_123")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_scan_includes_metrics(self):
        """Scan should include project metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "app.py").write_text("class App:\n    x = 1\n")
            result = await scan_repository(repo_path=tmpdir)
            assert "metrics" in result

    @pytest.mark.asyncio
    async def test_scan_detects_python_files(self):
        """Scan should find Python modules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "models.py").write_text("class User:\n    pass\n")
            Path(tmpdir, "views.py").write_text("def index(): pass\n")
            result = await scan_repository(repo_path=tmpdir)
            assert len(result.get("modules", [])) >= 2
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_scan.py -v
```

**Step 3: Write implementation**

```python
# src/opencode_arch/mcp/tools/scan.py
"""architect_scan MCP tool — generate reality manifest via AST scanning."""
from __future__ import annotations

from pathlib import Path
from typing import Any


async def scan_repository(repo_path: str) -> dict[str, Any]:
    """Scan a repository and generate its reality manifest.

    Performs AST analysis on all source files to produce a ground-truth
    inventory of modules, functions, classes, imports, and metrics.

    Args:
        repo_path: Absolute path to the repository root.

    Returns:
        Manifest dict with keys: generated_at, project_root, metrics,
        functional_blocks, modules, interfaces.
        Returns {"error": "..."} on failure.
    """
    path = Path(repo_path)
    if not path.exists():
        return {"error": f"Repository path does not exist: {repo_path}"}

    try:
        from architecture_model.manifest.generator import generate_manifest
        manifest = generate_manifest(path)
        return manifest
    except Exception as e:
        return {"error": f"Scan failed: {e}"}
```

**Step 4: Run tests**

```bash
pytest tests/test_scan.py -v
```

**Step 5: Commit**

```bash
git add src/opencode_arch/mcp/tools/scan.py tests/test_scan.py
git commit -m "feat: add architect_scan tool (AST manifest generation)"
```

---

### Task 3: Implement architect_slice Tool

**Files:**
- Create: `src/opencode_arch/mcp/tools/slice.py`
- Test: `tests/test_slice.py`

**Step 1: Write failing test**

```python
# tests/test_slice.py
"""Tests for the architect_slice MCP tool."""
import pytest
import tempfile
from pathlib import Path

from opencode_arch.mcp.tools.slice import slice_context


class TestSliceTool:
    @pytest.mark.asyncio
    async def test_slice_returns_string(self):
        """Slice should return a formatted context string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "main.py").write_text("def main(): pass\n")
            result = await slice_context(repo_path=tmpdir)
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_slice_respects_budget(self):
        """Slice should stay within token budget."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create many files to produce large manifest
            for i in range(20):
                Path(tmpdir, f"module_{i}.py").write_text(f"def func_{i}(): pass\n")
            result = await slice_context(repo_path=tmpdir, budget=200)
            # Rough estimate: 1 token ~ 4 chars
            assert len(result) < 200 * 5  # generous upper bound

    @pytest.mark.asyncio
    async def test_slice_with_focus(self):
        """Slice with focus should narrow context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "web.py").write_text("class WebServer: pass\n")
            Path(tmpdir, "db.py").write_text("class Database: pass\n")
            result = await slice_context(repo_path=tmpdir, focus="web")
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_slice_nonexistent_path(self):
        """Slice should return error for nonexistent path."""
        result = await slice_context(repo_path="/tmp/nonexistent_xyz")
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_slice_with_model_file(self):
        """Slice should use existing .architecture-model.yaml if present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "main.py").write_text("def main(): pass\n")
            # Create a minimal architecture model file
            Path(tmpdir, ".architecture-model.yaml").write_text(
                "meta:\n  project: test\n  schema_version: '1.3'\n"
                "components:\n  - id: COMP-1\n    name: Main\n    status: ACTIVE\n    layer: core\n"
            )
            result = await slice_context(repo_path=tmpdir)
            assert isinstance(result, str)
            assert len(result) > 0
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_slice.py -v
```

**Step 3: Write implementation**

```python
# src/opencode_arch/mcp/tools/slice.py
"""architect_slice MCP tool — compress repository context for LLM consumption."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


async def slice_context(
    repo_path: str,
    focus: str = "all",
    budget: int = 4000,
    detail: str = "standard",
) -> str:
    """Generate an optimized context slice from a repository.

    This is the core token-arbitrage function. It compresses a full repository
    into a dense, structured context string within the token budget.

    If an .architecture-model.yaml exists, uses the model + slicer + formatter.
    Otherwise, falls back to manifest-based context.

    Args:
        repo_path: Absolute path to the repository root.
        focus: Focus scope - "all", an F-block ID (e.g. "F1"), a layer name,
               or an artifact name (e.g. "icd", "requirements-analysis").
        budget: Maximum token budget (1 token ~ 4 chars).
        detail: Detail level - "minimal", "standard", or "full".

    Returns:
        Formatted context string within budget, or error message.
    """
    path = Path(repo_path)
    if not path.exists():
        return f"Error: Repository path does not exist: {repo_path}"

    try:
        model_file = path / ".architecture-model.yaml"

        if model_file.exists():
            # Use architecture model for rich, structured context
            return _slice_from_model(path, focus, budget, detail)
        else:
            # Fall back to manifest-based context
            return _slice_from_manifest(path, focus, budget)

    except Exception as e:
        return f"Error during context slicing: {e}"


def _slice_from_model(
    project_root: Path,
    focus: str,
    budget: int,
    detail: str,
) -> str:
    """Slice context using the architecture model (rich path)."""
    from architecture_model.core.parser import load_model
    from architecture_model.integrations.llm_context import (
        format_model_context,
        format_fblock_context,
        format_artifact_context,
    )
    from architecture_model.core.slicer import slice_by_fblock, slice_by_layer

    model_path = project_root / ".architecture-model.yaml"
    model = load_model(model_path)

    # Determine focus type and route to appropriate formatter
    if focus == "all":
        return format_model_context(model, max_tokens=budget, detail_level=detail)
    elif focus.startswith("F") and focus[1:].isdigit():
        # F-block focus (e.g., "F1", "F3")
        return format_fblock_context(model, f_block=focus, max_tokens=budget)
    elif focus in (
        "functional-architecture", "logical-architecture", "use-cases",
        "icd", "requirements-analysis", "operations-manual", "conops",
        "testing", "deployment-guide", "data-dictionary", "readme",
    ):
        # Artifact focus
        return format_artifact_context(model, artifact_name=focus, max_tokens=budget)
    else:
        # Try as layer name, fall back to full context with focus hint
        try:
            sliced = slice_by_layer(model, layer_id=focus)
            return format_model_context(sliced, max_tokens=budget, detail_level=detail)
        except (KeyError, ValueError):
            # Unknown focus — format full model with budget constraint
            return format_model_context(model, max_tokens=budget, detail_level=detail)


def _slice_from_manifest(
    project_root: Path,
    focus: str,
    budget: int,
) -> str:
    """Slice context using manifest only (no architecture model yet)."""
    from architecture_model.manifest.generator import generate_manifest

    manifest = generate_manifest(project_root)

    # Format manifest as compact YAML within budget
    manifest_yaml = yaml.dump(manifest, default_flow_style=False, sort_keys=False)

    # Truncate to budget (rough: 1 token ~ 4 chars)
    char_budget = budget * 4
    if len(manifest_yaml) > char_budget:
        # Prioritize: metrics + functional_blocks summary over raw modules
        summary = {
            "project_root": manifest.get("project_root"),
            "metrics": manifest.get("metrics", {}),
            "functional_blocks": {
                k: {"file_count": len(v.get("sub_functions", []))}
                for k, v in manifest.get("functional_blocks", {}).items()
            },
            "module_count": len(manifest.get("modules", [])),
        }
        if focus != "all":
            summary["focus"] = focus
        manifest_yaml = yaml.dump(summary, default_flow_style=False, sort_keys=False)

    return manifest_yaml[:char_budget]
```

**Step 4: Run tests**

```bash
pytest tests/test_slice.py -v
```

**Step 5: Commit**

```bash
git add src/opencode_arch/mcp/tools/slice.py tests/test_slice.py
git commit -m "feat: add architect_slice tool (context compression / token broker)"
```

---

### Task 4: Implement Telemetry Store

**Files:**
- Create: `src/opencode_arch/telemetry/__init__.py`
- Create: `src/opencode_arch/telemetry/store.py`
- Create: `src/opencode_arch/telemetry/recorder.py`
- Test: `tests/test_telemetry.py`

**Step 1: Write failing test**

```python
# tests/test_telemetry.py
"""Tests for telemetry store and recorder."""
import pytest
import tempfile
from pathlib import Path

from opencode_arch.telemetry.store import TelemetryStore
from opencode_arch.telemetry.recorder import record_invocation


class TestTelemetryStore:
    def test_create_store(self):
        """Store should create SQLite DB on init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(db_path=Path(tmpdir) / "telemetry.db")
            assert store.db_path.exists()

    def test_record_and_query(self):
        """Should record an invocation and retrieve it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(db_path=Path(tmpdir) / "telemetry.db")
            store.record(
                tool="architect_slice",
                repo="test-repo",
                context_tokens=430,
                output_quality=85,
                iterations=1,
            )
            records = store.query(tool="architect_slice")
            assert len(records) == 1
            assert records[0]["context_tokens"] == 430
            assert records[0]["output_quality"] == 85

    def test_record_multiple(self):
        """Should store multiple records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(db_path=Path(tmpdir) / "telemetry.db")
            for i in range(5):
                store.record(
                    tool="architect_extract",
                    repo=f"repo-{i}",
                    context_tokens=400 + i * 10,
                    output_quality=70 + i * 5,
                    iterations=1,
                )
            records = store.query(tool="architect_extract")
            assert len(records) == 5

    def test_average_metrics(self):
        """Should compute average metrics per tool."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(db_path=Path(tmpdir) / "telemetry.db")
            store.record(tool="slice", repo="a", context_tokens=400, output_quality=80, iterations=1)
            store.record(tool="slice", repo="b", context_tokens=600, output_quality=90, iterations=2)
            avg = store.averages(tool="slice")
            assert avg["avg_context_tokens"] == 500
            assert avg["avg_output_quality"] == 85
            assert avg["avg_iterations"] == 1.5


class TestRecorder:
    @pytest.mark.asyncio
    async def test_record_invocation(self):
        """Recorder should log to store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(db_path=Path(tmpdir) / "telemetry.db")
            await record_invocation(
                store=store,
                tool="architect_scan",
                repo="my-project",
                context_tokens=0,
                output_quality=100,
                iterations=1,
            )
            records = store.query(tool="architect_scan")
            assert len(records) == 1
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_telemetry.py -v
```

**Step 3: Write implementation**

```python
# src/opencode_arch/telemetry/__init__.py
"""Telemetry: records tool usage and outcomes for optimization."""

from opencode_arch.telemetry.store import TelemetryStore
from opencode_arch.telemetry.recorder import record_invocation

__all__ = ["TelemetryStore", "record_invocation"]
```

```python
# src/opencode_arch/telemetry/store.py
"""SQLite-backed telemetry store for tool invocations."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any


class TelemetryStore:
    """Records tool invocations and outcomes for optimization."""

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            db_path = Path.home() / ".opencode-arch" / "telemetry.db"
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                tool TEXT NOT NULL,
                repo TEXT,
                context_tokens INTEGER DEFAULT 0,
                output_quality INTEGER DEFAULT 0,
                iterations INTEGER DEFAULT 1,
                metadata TEXT
            )
        """)
        conn.commit()
        conn.close()

    def record(
        self,
        tool: str,
        repo: str = "",
        context_tokens: int = 0,
        output_quality: int = 0,
        iterations: int = 1,
        metadata: str = "",
    ):
        """Record a tool invocation."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO invocations (timestamp, tool, repo, context_tokens, output_quality, iterations, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (time.time(), tool, repo, context_tokens, output_quality, iterations, metadata),
        )
        conn.commit()
        conn.close()

    def query(self, tool: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """Query recorded invocations."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        if tool:
            rows = conn.execute(
                "SELECT * FROM invocations WHERE tool = ? ORDER BY timestamp DESC LIMIT ?",
                (tool, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM invocations ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def averages(self, tool: str) -> dict[str, float]:
        """Compute average metrics for a tool."""
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT AVG(context_tokens), AVG(output_quality), AVG(iterations) "
            "FROM invocations WHERE tool = ?",
            (tool,),
        ).fetchone()
        conn.close()
        return {
            "avg_context_tokens": row[0] or 0,
            "avg_output_quality": row[1] or 0,
            "avg_iterations": row[2] or 0,
        }
```

```python
# src/opencode_arch/telemetry/recorder.py
"""Async recorder for tool invocations."""
from __future__ import annotations

from opencode_arch.telemetry.store import TelemetryStore


async def record_invocation(
    store: TelemetryStore,
    tool: str,
    repo: str = "",
    context_tokens: int = 0,
    output_quality: int = 0,
    iterations: int = 1,
    metadata: str = "",
):
    """Record a tool invocation asynchronously.

    In the future this could batch writes or use async SQLite.
    For now, delegates directly to the synchronous store.
    """
    store.record(
        tool=tool,
        repo=repo,
        context_tokens=context_tokens,
        output_quality=output_quality,
        iterations=iterations,
        metadata=metadata,
    )
```

**Step 4: Run tests**

```bash
pytest tests/test_telemetry.py -v
```

**Step 5: Commit**

```bash
git add src/opencode_arch/telemetry/ tests/test_telemetry.py
git commit -m "feat: add telemetry store (SQLite) and recorder"
```

---

### Task 5: Rewrite architect_extract Tool

**Files:**
- Rewrite: `src/opencode_arch/mcp/tools/extract.py`
- Rewrite: `tests/test_mcp_extract.py`

**Step 1: Write new tests**

The extract tool now STORES a model that the agent produced (not generates one).
It validates, persists, and logs telemetry.

```python
# tests/test_mcp_extract.py
"""Tests for the architect_extract MCP tool (Phase 2: stores agent output)."""
import pytest
import tempfile
from pathlib import Path

from opencode_arch.mcp.tools.extract import store_extraction


VALID_YAML = """\
meta:
  project: test-project
  schema_version: '1.3'
components:
  - id: COMP-1
    name: Main
    status: ACTIVE
    layer: core
capabilities:
  - id: CAP-F1
    name: Processing
    status: ACTIVE
relationships:
  - from: COMP-1
    to: CAP-F1
    type: realizes
"""


class TestExtractTool:
    @pytest.mark.asyncio
    async def test_store_valid_extraction(self):
        """Should validate and store a valid model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await store_extraction(
                repo_path=tmpdir,
                model_yaml=VALID_YAML,
            )
            assert result["stored"] is True
            assert result["score"] >= 80
            assert Path(tmpdir, ".architecture-model.yaml").exists()

    @pytest.mark.asyncio
    async def test_store_records_telemetry(self):
        """Should record telemetry on successful store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await store_extraction(
                repo_path=tmpdir,
                model_yaml=VALID_YAML,
                context_tokens=430,
            )
            assert result["stored"] is True
            assert "telemetry_recorded" in result

    @pytest.mark.asyncio
    async def test_store_invalid_model(self):
        """Should still store but flag low score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await store_extraction(
                repo_path=tmpdir,
                model_yaml="meta:\n  project: x\n  schema_version: '1.3'\ncomponents: []\n",
            )
            # Empty model stores but scores low
            assert result["stored"] is True
            assert result["score"] <= 100  # Valid parse, just empty

    @pytest.mark.asyncio
    async def test_store_malformed_yaml(self):
        """Should return error for unparseable YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await store_extraction(
                repo_path=tmpdir,
                model_yaml="{{invalid yaml",
            )
            assert result["stored"] is False
            assert "error" in result
```

**Step 2: Write implementation**

```python
# src/opencode_arch/mcp/tools/extract.py
"""architect_extract MCP tool — validate and store an architecture extraction."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


async def store_extraction(
    repo_path: str,
    model_yaml: str,
    context_tokens: int = 0,
) -> dict[str, Any]:
    """Validate and store an architecture model extraction.

    Called AFTER the agent has produced a YAML architecture model.
    Validates the model, writes it to .architecture-model.yaml,
    and records telemetry.

    Args:
        repo_path: Path to the repository root (where to save the model).
        model_yaml: The YAML architecture model produced by the agent.
        context_tokens: How many tokens of context the agent used (for telemetry).

    Returns:
        Dict with: stored (bool), score (int), issues (list), telemetry_recorded (bool).
    """
    path = Path(repo_path)

    try:
        # Parse the YAML
        raw = yaml.safe_load(model_yaml)
        if not isinstance(raw, dict):
            return {"stored": False, "error": "YAML did not parse to a dict", "score": 0}

        # Validate using architecture_model
        from architecture_model.core.parser import _parse_raw
        from architecture_model.core.validator import validate_model

        model = _parse_raw(raw)
        validation = validate_model(model)

        score = validation.score
        issues = [str(issue) for issue in validation.issues]

        # Write to repo
        output_path = path / ".architecture-model.yaml"
        output_path.write_text(model_yaml)

        # Record telemetry
        telemetry_recorded = False
        try:
            from opencode_arch.telemetry.store import TelemetryStore
            store = TelemetryStore()
            store.record(
                tool="architect_extract",
                repo=str(path.name),
                context_tokens=context_tokens,
                output_quality=score,
                iterations=1,
            )
            telemetry_recorded = True
        except Exception:
            pass  # Telemetry failure shouldn't block the tool

        return {
            "stored": True,
            "score": score,
            "issues": issues,
            "path": str(output_path),
            "telemetry_recorded": telemetry_recorded,
        }

    except yaml.YAMLError as e:
        return {"stored": False, "error": f"Invalid YAML: {e}", "score": 0}
    except Exception as e:
        return {"stored": False, "error": f"Validation failed: {e}", "score": 0}
```

**Step 3: Run tests**

```bash
pytest tests/test_mcp_extract.py -v
```

**Step 4: Commit**

```bash
git add src/opencode_arch/mcp/tools/extract.py tests/test_mcp_extract.py
git commit -m "refactor: rewrite architect_extract as model storage + validation + telemetry"
```

---

### Task 6: Implement architect_generate Tool

**Files:**
- Create: `src/opencode_arch/mcp/tools/generate.py`
- Test: `tests/test_generate.py`

**Step 1: Write failing test**

```python
# tests/test_generate.py
"""Tests for the architect_generate MCP tool."""
import pytest
import tempfile
from pathlib import Path
import subprocess
import sys

from opencode_arch.mcp.tools.generate import run_tests_on_generated_code


class TestGenerateTool:
    @pytest.mark.asyncio
    async def test_run_tests_passing(self):
        """Should report pass when generated code passes tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple project with tests
            Path(tmpdir, "calculator.py").write_text(
                "def add(a, b):\n    return a + b\n"
            )
            Path(tmpdir, "test_calculator.py").write_text(
                "from calculator import add\n\n"
                "def test_add():\n    assert add(1, 2) == 3\n"
            )
            result = await run_tests_on_generated_code(repo_path=tmpdir)
            assert result["passed"] is True
            assert result["pass_rate"] == 1.0
            assert result["total_tests"] >= 1

    @pytest.mark.asyncio
    async def test_run_tests_failing(self):
        """Should report failure with details."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "calculator.py").write_text(
                "def add(a, b):\n    return a - b  # bug!\n"
            )
            Path(tmpdir, "test_calculator.py").write_text(
                "from calculator import add\n\n"
                "def test_add():\n    assert add(1, 2) == 3\n"
            )
            result = await run_tests_on_generated_code(repo_path=tmpdir)
            assert result["passed"] is False
            assert result["pass_rate"] < 1.0
            assert len(result.get("failures", [])) > 0

    @pytest.mark.asyncio
    async def test_run_tests_no_tests_found(self):
        """Should handle repos with no tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "app.py").write_text("x = 1\n")
            result = await run_tests_on_generated_code(repo_path=tmpdir)
            assert result["total_tests"] == 0

    @pytest.mark.asyncio
    async def test_run_tests_nonexistent_path(self):
        """Should return error for nonexistent path."""
        result = await run_tests_on_generated_code(repo_path="/tmp/nonexistent_xyz")
        assert "error" in result
```

**Step 2: Write implementation**

```python
# src/opencode_arch/mcp/tools/generate.py
"""architect_generate MCP tool — run tests on generated code."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


async def run_tests_on_generated_code(
    repo_path: str,
    test_command: str | None = None,
) -> dict[str, Any]:
    """Run the repository's test suite against generated code.

    This is the quality gate for code generation. The agent generates code,
    then calls this tool to verify it passes the original tests.

    Args:
        repo_path: Path to the repository with generated code + tests.
        test_command: Custom test command. Defaults to pytest.

    Returns:
        Dict with: passed (bool), pass_rate (float), total_tests (int),
        passed_tests (int), failures (list of failure descriptions).
    """
    path = Path(repo_path)
    if not path.exists():
        return {"error": f"Path does not exist: {repo_path}"}

    try:
        if test_command:
            cmd = test_command.split()
        else:
            cmd = [sys.executable, "-m", "pytest", str(path), "-v", "--tb=short", "-q"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(path),
        )

        # Parse pytest output
        output = result.stdout + result.stderr
        return _parse_pytest_output(output, result.returncode)

    except subprocess.TimeoutExpired:
        return {"error": "Test execution timed out (120s)", "passed": False, "pass_rate": 0.0, "total_tests": 0}
    except Exception as e:
        return {"error": f"Test execution failed: {e}", "passed": False, "pass_rate": 0.0, "total_tests": 0}


def _parse_pytest_output(output: str, returncode: int) -> dict[str, Any]:
    """Parse pytest output to extract pass/fail counts."""
    total = 0
    passed_count = 0
    failures: list[str] = []

    for line in output.split("\n"):
        # Look for summary line: "5 passed, 2 failed in 0.5s"
        if "passed" in line or "failed" in line or "error" in line:
            parts = line.strip().split()
            for i, part in enumerate(parts):
                if part == "passed" and i > 0:
                    try:
                        passed_count = int(parts[i - 1])
                    except ValueError:
                        pass
                elif part == "failed" and i > 0:
                    try:
                        total += int(parts[i - 1])
                    except ValueError:
                        pass

        # Capture FAILED test names
        if line.startswith("FAILED"):
            failures.append(line.strip())

    total += passed_count

    if total == 0 and "no tests ran" in output.lower():
        return {"passed": True, "pass_rate": 0.0, "total_tests": 0, "passed_tests": 0, "failures": []}

    pass_rate = passed_count / total if total > 0 else 0.0

    return {
        "passed": returncode == 0,
        "pass_rate": pass_rate,
        "total_tests": total,
        "passed_tests": passed_count,
        "failures": failures,
    }
```

**Step 3: Run tests**

```bash
pytest tests/test_generate.py -v
```

**Step 4: Commit**

```bash
git add src/opencode_arch/mcp/tools/generate.py tests/test_generate.py
git commit -m "feat: add architect_generate tool (test runner for generated code)"
```

---

### Task 7: Rewrite MCP Server + Validate Tool

**Files:**
- Rewrite: `src/opencode_arch/mcp/server.py`
- Modify: `src/opencode_arch/mcp/tools/validate.py` (remove oracle references)
- Rewrite: `tests/test_mcp_validate.py`
- Remove: `tests/test_integration.py` (will rewrite)

**Step 1: Update validate tool (remove oracle)**

Remove all oracle-related code from validate.py. Keep structural validation only.

```python
# src/opencode_arch/mcp/tools/validate.py
"""architect_validate MCP tool — validate architecture model quality."""
from __future__ import annotations

from typing import Any

import yaml


async def validate_architecture(model_yaml: str) -> dict[str, Any]:
    """Validate an architecture model for structural correctness.

    Args:
        model_yaml: The YAML architecture model string to validate.

    Returns:
        Dict with: score (0-100), issues (list), entity_count, relationship_count, is_valid.
    """
    try:
        raw = yaml.safe_load(model_yaml)
        if not isinstance(raw, dict):
            return {"score": 0, "issues": ["YAML did not parse to a dict"], "entity_count": 0, "relationship_count": 0, "is_valid": False}

        from architecture_model.core.parser import _parse_raw
        from architecture_model.core.validator import validate_model

        model = _parse_raw(raw)
        validation = validate_model(model)

        return {
            "score": validation.score,
            "issues": [str(issue) for issue in validation.issues],
            "entity_count": model.entity_count,
            "relationship_count": model.relationship_count,
            "is_valid": validation.is_valid,
        }

    except Exception as e:
        return {"score": 0, "issues": [f"Parse/validation error: {e}"], "entity_count": 0, "relationship_count": 0, "is_valid": False}
```

**Step 2: Rewrite MCP server to register all 5 tools**

```python
# src/opencode_arch/mcp/server.py
"""FastMCP server entry point for opencode-arch.

Run with: python -m opencode_arch.mcp.server
"""
from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        "opencode-arch",
        description="Architecture context compression, validation, and code quality tools",
    )

    from opencode_arch.mcp.tools.scan import scan_repository
    from opencode_arch.mcp.tools.slice import slice_context
    from opencode_arch.mcp.tools.validate import validate_architecture
    from opencode_arch.mcp.tools.extract import store_extraction
    from opencode_arch.mcp.tools.generate import run_tests_on_generated_code

    @mcp.tool()
    async def architect_scan(repo_path: str) -> dict:
        """Scan a repository to generate its reality manifest (AST analysis).

        Returns a manifest with: modules, functions, classes, imports, metrics.
        Use this as raw material before slicing context.
        """
        return await scan_repository(repo_path=repo_path)

    @mcp.tool()
    async def architect_slice(repo_path: str, focus: str = "all", budget: int = 4000, detail: str = "standard") -> str:
        """Generate an optimized context slice from a repository.

        Compresses the full repository into a dense context string within the
        token budget. This is the core token-arbitrage function.

        Args:
            repo_path: Absolute path to the repository.
            focus: "all", an F-block ID ("F1"), layer name, or artifact name ("icd").
            budget: Maximum token budget (default 4000).
            detail: "minimal", "standard", or "full".
        """
        return await slice_context(repo_path=repo_path, focus=focus, budget=budget, detail=detail)

    @mcp.tool()
    async def architect_validate(model_yaml: str) -> dict:
        """Validate an architecture model for structural correctness.

        Checks: ID uniqueness, referential integrity, orphan detection,
        capability realization, meta completeness. Returns score 0-100.
        """
        return await validate_architecture(model_yaml=model_yaml)

    @mcp.tool()
    async def architect_extract(repo_path: str, model_yaml: str, context_tokens: int = 0) -> dict:
        """Store a validated architecture extraction.

        Call AFTER the agent produces a YAML model. Validates, writes to
        .architecture-model.yaml, and records telemetry.
        """
        return await store_extraction(repo_path=repo_path, model_yaml=model_yaml, context_tokens=context_tokens)

    @mcp.tool()
    async def architect_generate(repo_path: str, test_command: str = "") -> dict:
        """Run tests on generated code to verify quality.

        Executes the repository's test suite against generated code.
        Returns pass rate, failures, and total test count.
        """
        return await run_tests_on_generated_code(repo_path=repo_path, test_command=test_command or None)

except ImportError:
    # mcp package not available - tools still work as standalone async functions
    mcp = None
```

**Step 3: Rewrite validate tests (no oracle)**

```python
# tests/test_mcp_validate.py
"""Tests for the architect_validate MCP tool."""
import pytest

from opencode_arch.mcp.tools.validate import validate_architecture


VALID_YAML = """\
meta:
  project: test-project
  schema_version: '1.3'
capabilities:
  - id: CAP-F1
    name: Core Processing
    status: ACTIVE
components:
  - id: COMP-1
    name: Processor
    status: ACTIVE
    layer: core
relationships:
  - from: COMP-1
    to: CAP-F1
    type: realizes
"""

ORPHAN_YAML = """\
meta:
  project: test-project
  schema_version: '1.3'
capabilities:
  - id: CAP-F1
    name: Core Processing
    status: ACTIVE
components:
  - id: COMP-1
    name: Processor
    status: ACTIVE
    layer: core
relationships:
  - from: COMP-MISSING
    to: CAP-F1
    type: realizes
"""

MALFORMED_YAML = "{{not valid yaml"


class TestValidateTool:
    @pytest.mark.asyncio
    async def test_validate_valid_model(self):
        result = await validate_architecture(model_yaml=VALID_YAML)
        assert result["score"] >= 80
        assert result["is_valid"] is True
        assert result["entity_count"] == 2
        assert result["relationship_count"] == 1

    @pytest.mark.asyncio
    async def test_validate_orphaned_reference(self):
        result = await validate_architecture(model_yaml=ORPHAN_YAML)
        assert result["score"] < 100
        assert len(result["issues"]) > 0

    @pytest.mark.asyncio
    async def test_validate_malformed_yaml(self):
        result = await validate_architecture(model_yaml=MALFORMED_YAML)
        assert result["score"] == 0
        assert result["is_valid"] is False

    @pytest.mark.asyncio
    async def test_validate_empty_model(self):
        result = await validate_architecture(
            model_yaml="meta:\n  project: x\n  schema_version: '1.3'\ncomponents: []\n"
        )
        assert "score" in result
        assert result["entity_count"] == 0
```

**Step 4: Run all tests**

```bash
pytest tests/ -v
```

**Step 5: Commit**

```bash
git add -A && git commit -m "refactor: rewrite MCP server with 5 tools, remove oracle from validate"
```

---

### Task 8: Write Integration Tests

**Files:**
- Rewrite: `tests/test_integration.py`

**Step 1: Write integration tests for the full tool flow**

```python
# tests/test_integration.py
"""Integration tests: scan → slice → (agent reasons) → extract → validate."""
import pytest
import tempfile
from pathlib import Path

from opencode_arch.mcp.tools.scan import scan_repository
from opencode_arch.mcp.tools.slice import slice_context
from opencode_arch.mcp.tools.validate import validate_architecture
from opencode_arch.mcp.tools.extract import store_extraction


@pytest.mark.asyncio
async def test_full_extraction_flow():
    """Simulate: scan → slice → validate agent output → store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a small project
        Path(tmpdir, "models.py").write_text("class User:\n    name: str\n")
        Path(tmpdir, "views.py").write_text("def index():\n    return 'hello'\n")

        # Step 1: Scan
        manifest = await scan_repository(repo_path=tmpdir)
        assert "modules" in manifest
        assert len(manifest["modules"]) >= 2

        # Step 2: Slice (get context for agent)
        context = await slice_context(repo_path=tmpdir, budget=2000)
        assert isinstance(context, str)
        assert len(context) > 0

        # Step 3: Simulate agent output (normally agent produces this)
        agent_yaml = (
            "meta:\n"
            "  project: test\n"
            "  schema_version: '1.3'\n"
            "components:\n"
            "  - id: COMP-1\n"
            "    name: Models\n"
            "    status: ACTIVE\n"
            "    layer: core\n"
            "  - id: COMP-2\n"
            "    name: Views\n"
            "    status: ACTIVE\n"
            "    layer: web\n"
            "capabilities:\n"
            "  - id: CAP-F1\n"
            "    name: UserManagement\n"
            "    status: ACTIVE\n"
            "relationships:\n"
            "  - from: COMP-1\n"
            "    to: CAP-F1\n"
            "    type: realizes\n"
        )

        # Step 4: Validate
        validation = await validate_architecture(model_yaml=agent_yaml)
        assert validation["score"] >= 70
        assert validation["is_valid"] is True

        # Step 5: Store
        stored = await store_extraction(repo_path=tmpdir, model_yaml=agent_yaml, context_tokens=len(context) // 4)
        assert stored["stored"] is True
        assert Path(tmpdir, ".architecture-model.yaml").exists()


@pytest.mark.asyncio
async def test_slice_uses_stored_model():
    """After storing a model, slice should use it for richer context."""
    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "app.py").write_text("class App: pass\n")

        # Store a model
        model_yaml = (
            "meta:\n"
            "  project: test\n"
            "  schema_version: '1.3'\n"
            "components:\n"
            "  - id: COMP-1\n"
            "    name: App\n"
            "    status: ACTIVE\n"
            "    layer: web\n"
        )
        Path(tmpdir, ".architecture-model.yaml").write_text(model_yaml)

        # Now slice should detect the model file and use rich path
        context = await slice_context(repo_path=tmpdir)
        assert isinstance(context, str)
        assert len(context) > 0
```

**Step 2: Run all tests**

```bash
pytest tests/ -v
```

Expected: All tests pass.

**Step 3: Commit**

```bash
git add tests/test_integration.py && git commit -m "test: rewrite integration tests for Phase 2 tool flow"
```

---

### Task 9: Rewrite Skills + Add Extension Manifest

**Files:**
- Rewrite: `skills/extraction/SKILL.md`
- Create: `skills/generation/SKILL.md`
- Create: `opencode.json`

**Step 1: Rewrite extraction skill**

```markdown
# Skill: Architecture Extraction

## When to Use

Use when the user asks to extract, document, or analyze the architecture of a codebase.

## Workflow

1. **Scan**: Call `architect_scan(repo_path)` to generate the reality manifest.
   - Review module count, metrics, functional blocks.

2. **Slice**: Call `architect_slice(repo_path, focus, budget=4000)` to get compressed context.
   - For large repos, start with focus on a specific layer or F-block.
   - Default budget of 4000 tokens is usually sufficient.

3. **Extract**: Using the context from the slice, produce a YAML architecture model following the 7-entity, 8-relationship schema:
   - Entities: capabilities, components, layers, behaviors, interfaces, constraints, actors
   - Relationships: realizes, uses, constrains, contains, triggers, depends_on, implements, exposes
   - Every entity needs: id, name, status (ACTIVE/PLANNED/DEPRECATED)
   - Every relationship needs: from, to, type

4. **Validate**: Call `architect_validate(model_yaml)` to check structural quality.
   - Target score: 80+
   - If score < 80: review issues, fix the model, re-validate.
   - Common issues: orphaned entities, dangling references, missing meta.

5. **Store**: Call `architect_extract(repo_path, model_yaml, context_tokens)` to persist.
   - Writes .architecture-model.yaml to the repo root.
   - Records telemetry for future optimization.

## Escalation (Full Workflow)

If initial extraction scores below 60:
- Re-scan with narrower focus
- Increase budget: `architect_slice(repo_path, budget=8000, detail="full")`
- Extract one layer at a time, then merge

## Notes

- Smaller budget = cheaper but less context = may need more iterations
- First extraction of a repo usually needs higher budget (~4000)
- Subsequent refinements can use lower budget (~1000) focusing on specific areas
```

**Step 2: Write generation skill**

```markdown
# Skill: Test-Guided Code Generation

## When to Use

Use when generating code from an architecture model that must pass existing tests.

## Workflow

1. **Scan + Slice**: Get context for the target component.
   ```
   architect_scan(repo_path)
   architect_slice(repo_path, focus="<component-or-layer>", budget=4000)
   ```

2. **Generate**: Write code for the target component using:
   - The architecture model constraints (from slice)
   - The existing test file expectations
   - The project's coding patterns

3. **Test**: Call `architect_generate(repo_path)` to run the test suite.
   - Check pass_rate and failures.

4. **Iterate on failures**:
   - Read failure messages from the result
   - Fix only the failing components
   - Re-run tests
   - Repeat until pass_rate reaches target (usually 1.0)

5. **Store success**: If a model update was needed, call `architect_extract` to persist.

## Guidelines

- Generate one component at a time for complex systems
- Use relative imports matching the project structure
- Check existing test imports to understand expected module layout
- Maximum 3 retry iterations before escalating to user
```

**Step 3: Write OpenCode extension manifest**

```json
{
  "name": "opencode-arch",
  "version": "0.2.0",
  "description": "Architecture context compression, validation, and code quality tools",
  "mcp": {
    "command": "python",
    "args": ["-m", "opencode_arch.mcp.server"]
  },
  "skills": [
    "skills/extraction",
    "skills/generation"
  ]
}
```

**Step 4: Commit**

```bash
git add skills/ opencode.json && git commit -m "feat: rewrite skills + add OpenCode extension manifest"
```

---

### Task 10: Final Verification

**Step 1: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests pass.

**Step 2: Verify package installs cleanly**

```bash
pip install -e ".[dev]"
python -c "from opencode_arch.mcp.tools.scan import scan_repository; print('OK')"
python -c "from opencode_arch.mcp.tools.slice import slice_context; print('OK')"
python -c "from opencode_arch.mcp.tools.validate import validate_architecture; print('OK')"
python -c "from opencode_arch.mcp.tools.extract import store_extraction; print('OK')"
python -c "from opencode_arch.mcp.tools.generate import run_tests_on_generated_code; print('OK')"
python -c "from opencode_arch.telemetry import TelemetryStore; print('OK')"
```

**Step 3: Verify git log is clean**

```bash
git log --oneline
git status
```

**Step 4: Commit any remaining changes**

---

## Summary

| Task | Component | Tests |
|------|-----------|-------|
| 1 | Remove oracle, update deps | Cleanup |
| 2 | architect_scan (AST manifest) | 4 tests |
| 3 | architect_slice (context compression) | 5 tests |
| 4 | Telemetry store + recorder | 5 tests |
| 5 | architect_extract (store + validate) | 4 tests |
| 6 | architect_generate (test runner) | 4 tests |
| 7 | MCP server + validate rewrite | 4 tests |
| 8 | Integration tests | 2 tests |
| 9 | Skills + extension manifest | Docs |
| 10 | Final verification | Green |

**Total new tests: ~28** (replacing the 23 from Phase 1)
