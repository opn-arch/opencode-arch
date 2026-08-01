# Proof of Value Metric Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Surface compression ratio and token savings to users everywhere they interact with the tool — CLI output, health report, MCP tool responses, and a dedicated stats display.

**Architecture:** Add `compute_compression_stats()` utility, wire into: (1) `init` command output, (2) health report generator, (3) `architect_slice` MCP tool response, (4) new `architecture-model stats` enhanced output.

**Tech Stack:** Python

**Repos:**
- `architecture-model-standard` @ `/Users/baigm2/Documents/Projects/architecture-model-standard/`
- `opencode-arch` @ `/Users/baigm2/Documents/Projects/opencode-arch/`
- Tests: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`

---

### Task 1: Create compression stats utility

**Files:**
- Create: `src/architecture_model/core/compression.py`
- Test: `tests/test_compression_stats.py`

**Step 1: Write failing test**

```python
"""Tests for compression stats utility."""
import tempfile
from pathlib import Path

import pytest

from architecture_model.core.compression import compute_compression_stats


@pytest.fixture
def sample_project(tmp_path):
    """Create a project with known sizes."""
    # Source files: 1000 bytes each × 5 = 5000 bytes
    src = tmp_path / "src"
    src.mkdir()
    for i in range(5):
        (src / f"module{i}.py").write_text("x" * 1000)
    
    # Model file: 500 bytes
    models = tmp_path / ".architecture-models"
    models.mkdir()
    (models / "manifest.yaml").write_text("y" * 500)
    
    return tmp_path


def test_compression_stats_basic(sample_project):
    stats = compute_compression_stats(sample_project)
    assert stats["source_bytes"] == 5000
    assert stats["model_bytes"] == 500
    assert stats["compression_ratio"] == 10.0
    assert stats["source_tokens"] == 1250  # 5000 / 4
    assert stats["model_tokens"] == 125    # 500 / 4
    assert stats["tokens_saved"] == 1125


def test_compression_stats_empty_project(tmp_path):
    stats = compute_compression_stats(tmp_path)
    assert stats["source_bytes"] == 0
    assert stats["compression_ratio"] == 0.0


def test_compression_stats_no_model(tmp_path):
    (tmp_path / "main.py").write_text("x" * 100)
    stats = compute_compression_stats(tmp_path)
    assert stats["source_bytes"] == 100
    assert stats["model_bytes"] == 0
    assert stats["compression_ratio"] == 0.0


def test_compression_stats_excludes_vendor(tmp_path):
    (tmp_path / "main.py").write_text("x" * 100)
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "lib.py").write_text("x" * 9000)  # should be excluded
    stats = compute_compression_stats(tmp_path)
    assert stats["source_bytes"] == 100


def test_format_compression_summary():
    from architecture_model.core.compression import format_compression_summary
    stats = {
        "source_bytes": 50000,
        "model_bytes": 1000,
        "compression_ratio": 50.0,
        "source_tokens": 12500,
        "model_tokens": 250,
        "tokens_saved": 12250,
    }
    summary = format_compression_summary(stats)
    assert "50.0x" in summary
    assert "12,250" in summary or "12250" in summary
```

**Step 2: Implement**

```python
"""Compression statistics for architecture models.

Computes and formats token savings to demonstrate value to users.
"""
from __future__ import annotations

from pathlib import Path

SOURCE_EXTENSIONS = {"*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.go", "*.rs", "*.java", "*.kt", "*.swift"}
EXCLUDE_DIRS = {"node_modules", ".git", "vendor", "_vendor", "vendored", "__pycache__", "dist", "build", ".venv", "venv"}
CHARS_PER_TOKEN = 4


def compute_compression_stats(root: Path) -> dict:
    """Compute compression ratio between source code and model representation.
    
    Returns dict with: source_bytes, model_bytes, compression_ratio,
    source_tokens, model_tokens, tokens_saved.
    """
    source_bytes = _sum_source_size(root)
    model_bytes = _sum_model_size(root)
    
    source_tokens = source_bytes // CHARS_PER_TOKEN
    model_tokens = model_bytes // CHARS_PER_TOKEN
    tokens_saved = max(0, source_tokens - model_tokens)
    
    if model_bytes > 0:
        compression_ratio = round(source_bytes / model_bytes, 1)
    else:
        compression_ratio = 0.0
    
    return {
        "source_bytes": source_bytes,
        "model_bytes": model_bytes,
        "compression_ratio": compression_ratio,
        "source_tokens": source_tokens,
        "model_tokens": model_tokens,
        "tokens_saved": tokens_saved,
    }


def format_compression_summary(stats: dict) -> str:
    """Format stats as human-readable summary string."""
    if stats["compression_ratio"] == 0.0:
        return "No model found — run 'architecture-model init .' to generate."
    
    lines = [
        "--- Token Savings ---",
        f"  Source code: ~{stats['source_tokens']:,} tokens ({stats['source_bytes']:,} bytes)",
        f"  Model:       ~{stats['model_tokens']:,} tokens ({stats['model_bytes']:,} bytes)",
        f"  Compression: {stats['compression_ratio']}x ({stats['tokens_saved']:,} tokens saved)",
    ]
    
    # Contextual message based on ratio
    ratio = stats["compression_ratio"]
    if ratio >= 50:
        lines.append(f"  Note: High compression ({ratio}x). Consider per-block slicing for accuracy.")
    elif ratio >= 10:
        lines.append(f"  Quality: Good compression range for accurate architecture reasoning.")
    
    return "\n".join(lines)


def _sum_source_size(root: Path) -> int:
    """Sum all source file sizes, excluding vendor/generated."""
    total = 0
    for ext in SOURCE_EXTENSIONS:
        for f in root.rglob(ext):
            if any(p in f.parts for p in EXCLUDE_DIRS):
                continue
            # Skip files inside .architecture-models
            if ".architecture-models" in f.parts:
                continue
            try:
                total += f.stat().st_size
            except OSError:
                continue
    return total


def _sum_model_size(root: Path) -> int:
    """Sum architecture model file sizes."""
    total = 0
    models_dir = root / ".architecture-models"
    if models_dir.is_dir():
        for f in models_dir.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    continue
    
    # Also count top-level model files
    for name in (".architecture-model-extracted.yaml", ".architecture-model.yaml"):
        candidate = root / name
        if candidate.is_file():
            try:
                total += candidate.stat().st_size
            except OSError:
                pass
    
    return total
```

**Step 3: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_compression_stats.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add src/architecture_model/core/compression.py tests/test_compression_stats.py
git commit -m "feat: add compression stats utility for token savings display"
```

---

### Task 2: Wire into health report

**Files:**
- Modify: `src/architecture_model/docs/health.py`

**Step 1: Add compression section to health report**

Add after the existing content in `generate_health_report()`:

```python
# At the top, add import:
from ..core.compression import compute_compression_stats, format_compression_summary

# At the end of the report generation, add section:
def _compression_section(root: Path | None) -> str:
    if root is None:
        return ""
    stats = compute_compression_stats(root)
    if stats["compression_ratio"] == 0.0:
        return ""
    lines = [
        "",
        "## Token Savings",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Source code | ~{stats['source_tokens']:,} tokens |",
        f"| Architecture model | ~{stats['model_tokens']:,} tokens |",
        f"| **Compression ratio** | **{stats['compression_ratio']}x** |",
        f"| **Tokens saved per query** | **{stats['tokens_saved']:,}** |",
        "",
    ]
    return "\n".join(lines)
```

Modify `generate_health_report` signature to accept optional `root: Path | None = None` parameter.

**Step 2: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_docs_gen.py -v`
Expected: PASS (existing tests shouldn't break since root defaults to None)

**Step 3: Commit**

```bash
git add src/architecture_model/docs/health.py
git commit -m "feat: add token savings section to health report"
```

---

### Task 3: Wire into architect_slice MCP response

**Files:**
- Modify (opencode-arch): `src/opencode_arch/mcp/tools/slice.py`

**Step 1: Add compression stats to slice response**

The slice tool already computes compression ratio. Ensure it's included in the response dict. Check current return format and add a `compression_stats` field:

```python
# Add to the return value of slice_context():
return {
    "context": context_str,
    "tokens_used": tokens_used,
    "compression_ratio": ratio,
    "tokens_saved": source_tokens - tokens_used,
    "source_tokens": source_tokens,
}
```

**Step 2: Run opencode-arch tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_slice.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add src/opencode_arch/mcp/tools/slice.py
git commit -m "feat: include compression stats in architect_slice response"
```

---

### Task 4: Enhanced stats CLI command

**Files:**
- Modify: `src/architecture_model/cli/main.py` (the `_cmd_stats` handler)

**Step 1: Add compression stats to stats command output**

The existing `stats` command shows model statistics. Enhance it to also show compression ratio when a project root is available:

```python
# Add to _cmd_stats:
from ..core.compression import compute_compression_stats, format_compression_summary

# After existing stats output:
# Try to find project root from model path
model_path = Path(args.model).resolve()
root_candidates = [model_path.parent, model_path.parent.parent]
for root in root_candidates:
    if (root / ".architecture-model.yaml").exists():
        stats = compute_compression_stats(root)
        if stats["compression_ratio"] > 0:
            print()
            print(format_compression_summary(stats))
        break
```

**Step 2: Commit**

```bash
git add src/architecture_model/cli/main.py
git commit -m "feat: show compression ratio in stats command"
```
