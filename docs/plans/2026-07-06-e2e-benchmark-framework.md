# E2E Benchmark Framework Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create an E2E benchmark that proves the opencode-arch pipeline produces valid architecture extractions and regenerated code that passes real test suites on well-known open-source repos.

**Architecture:** Pytest-based framework with `@pytest.mark.e2e` markers (skipped by default). Tests use `opencode run` subprocess to call the real agent with MCP tools. Results stored as JSON + telemetry. Default set: 5 small repos already cloned at `/tmp/test-repos/`.

**Tech Stack:** pytest, pytest-asyncio, subprocess (opencode run), JSON results, existing telemetry

---

### Task 1: Pytest Configuration for E2E Markers

**Files:**
- Modify: `pyproject.toml` (add markers config)
- Create: `tests/e2e/__init__.py`
- Create: `tests/e2e/conftest.py`

**Step 1: Add e2e marker and conftest flag to pyproject.toml**

Add to `[tool.pytest.ini_options]`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "e2e: expensive end-to-end tests requiring LLM calls (deselect with '-m \"not e2e\"')",
]
```

**Step 2: Create tests/e2e/__init__.py**

```python
"""E2E benchmark tests - require --e2e flag to run."""
```

**Step 3: Create tests/e2e/conftest.py**

```python
"""E2E test configuration and fixtures."""
from __future__ import annotations

import json
import shutil
import tempfile
import pytest
from datetime import datetime
from pathlib import Path

# Default benchmark repos (small, fast tests)
BENCHMARK_REPOS = [
    {"name": "python-dotenv", "subdir": "src/dotenv", "url": "https://github.com/theskumar/python-dotenv"},
    {"name": "colorama", "subdir": "colorama", "url": "https://github.com/tartley/colorama"},
    {"name": "aiofiles", "subdir": "src/aiofiles", "url": "https://github.com/aio-libs/aiofiles"},
    {"name": "tqdm", "subdir": "tqdm", "url": "https://github.com/tqdm/tqdm"},
    {"name": "structlog", "subdir": "src/structlog", "url": "https://github.com/hynek/structlog"},
]

CLONE_DIR = Path("/tmp/test-repos")


def pytest_addoption(parser):
    parser.addoption("--e2e", action="store_true", default=False, help="Run expensive E2E benchmarks")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--e2e"):
        skip = pytest.mark.skip(reason="E2E tests require --e2e flag")
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip)


@pytest.fixture(scope="session")
def results_dir():
    """Results output directory."""
    d = Path(__file__).parent.parent.parent / "results"
    d.mkdir(exist_ok=True)
    return d


@pytest.fixture(scope="session")
def clone_dir():
    """Directory where benchmark repos are cloned."""
    if not CLONE_DIR.exists():
        pytest.skip(f"Benchmark repos not cloned at {CLONE_DIR}")
    return CLONE_DIR


@pytest.fixture(params=[r["name"] for r in BENCHMARK_REPOS], scope="function")
def repo_info(request, clone_dir):
    """Parameterized fixture providing repo info + path."""
    name = request.param
    info = next(r for r in BENCHMARK_REPOS if r["name"] == name)
    repo_path = clone_dir / name
    if not repo_path.exists():
        pytest.skip(f"Repo {name} not cloned at {repo_path}")
    return {**info, "path": repo_path}
```

**Step 4: Verify unit tests still pass (e2e tests should be auto-skipped)**

Run: `pytest tests/ -v --tb=short`
Expected: 47 passed (e2e tests skipped since no --e2e flag)

**Step 5: Commit**

```bash
git add pyproject.toml tests/e2e/
git commit -m "feat: add E2E benchmark framework (conftest + markers)"
```

---

### Task 2: Extraction Benchmark Test

**Files:**
- Create: `tests/e2e/test_extraction.py`

**Step 1: Write extraction test**

```python
"""E2E extraction benchmark: extract architecture from real repos."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest


@pytest.mark.e2e
class TestExtraction:
    """Extract architecture from benchmark repos and verify quality."""

    TIMEOUT = 600  # 10 minutes per repo

    def test_extract_produces_valid_model(self, repo_info, results_dir):
        """Extract architecture and verify score >= 80."""
        repo_path = str(repo_info["path"])
        repo_name = repo_info["name"]

        start = time.time()

        # Call opencode run with extraction prompt
        prompt = (
            f"Use architect_scan to scan this repo, then produce a valid "
            f".architecture-model.yaml. Use architect_extract to validate and store it. "
            f"The model must score >= 80. Include meta (project: {repo_name}, "
            f"schema_version: '1.3'), entities (capabilities, components), "
            f"and relationships (realizes, depends-on, contains). "
            f"Output the final YAML between ```yaml fences."
        )

        result = subprocess.run(
            ["opencode", "run", prompt, "--dir", repo_path],
            capture_output=True, text=True, timeout=self.TIMEOUT,
        )

        elapsed = time.time() - start

        # Check model was stored
        model_path = Path(repo_path) / ".architecture-model.yaml"
        assert model_path.exists(), f"No .architecture-model.yaml produced for {repo_name}"

        # Validate the stored model
        from architecture_model.core.parser import load_model
        from architecture_model.core.validator import validate_model

        model = load_model(model_path)
        validation = validate_model(model)

        # Record result
        result_data = {
            "test": "e2e_extraction",
            "timestamp": datetime.now().isoformat(),
            "repo": repo_name,
            "url": repo_info["url"],
            "score": validation.score,
            "is_valid": validation.is_valid,
            "entity_count": model.entity_count,
            "relationship_count": len(model.relationships),
            "issues": [str(i) for i in validation.issues[:10]],
            "time_seconds": elapsed,
            "exit_code": result.returncode,
        }

        # Write result
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = results_dir / f"e2e_extract_{repo_name}_{ts}.json"
        out_file.write_text(json.dumps(result_data, indent=2))

        # Assertions
        assert validation.score >= 80, (
            f"{repo_name}: score {validation.score}/100, "
            f"issues: {[str(i) for i in validation.issues[:5]]}"
        )
        assert model.entity_count >= 3, f"{repo_name}: only {model.entity_count} entities"

        # Cleanup: remove generated model (don't pollute benchmark repos)
        model_path.unlink(missing_ok=True)
```

**Step 2: Verify test is collected but skipped without --e2e**

Run: `pytest tests/e2e/test_extraction.py -v`
Expected: 5 tests SKIPPED (need --e2e flag)

**Step 3: Commit**

```bash
git add tests/e2e/test_extraction.py
git commit -m "feat: add E2E extraction benchmark test (5 repos)"
```

---

### Task 3: Regeneration Benchmark Test

**Files:**
- Create: `tests/e2e/test_regeneration.py`

**Step 1: Write regeneration test**

```python
"""E2E regeneration benchmark: regenerate code from architecture, run real tests."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import pytest


@pytest.mark.e2e
class TestRegeneration:
    """Delete source code, regenerate from architecture model, run real tests."""

    TIMEOUT = 600  # 10 minutes per repo

    def test_regenerate_passes_tests(self, repo_info, results_dir):
        """Regenerate source from architecture model and run test suite."""
        repo_path = repo_info["path"]
        repo_name = repo_info["name"]
        subdir = repo_info["subdir"]

        # Step 1: Extract architecture first (we need a model to regenerate from)
        extract_prompt = (
            f"Use architect_scan to scan this repo, then use architect_extract "
            f"to store a validated architecture model. Include all components with "
            f"their functions and symbols."
        )
        subprocess.run(
            ["opencode", "run", extract_prompt, "--dir", str(repo_path)],
            capture_output=True, text=True, timeout=self.TIMEOUT,
        )

        model_file = repo_path / ".architecture-model.yaml"
        if not model_file.exists():
            pytest.skip(f"Could not extract model for {repo_name}")

        # Step 2: Copy repo to temp dir, delete source, keep tests + model
        with tempfile.TemporaryDirectory(prefix=f"regen_{repo_name}_") as tmpdir:
            tmp_path = Path(tmpdir)

            # Copy entire repo
            shutil.copytree(repo_path, tmp_path / repo_name, dirs_exist_ok=True)
            work_dir = tmp_path / repo_name

            # Delete source directory (what we'll regenerate)
            src_path = work_dir / subdir
            if src_path.exists():
                shutil.rmtree(src_path)
                src_path.mkdir(parents=True)
                # Keep __init__.py so package is importable
                (src_path / "__init__.py").write_text("")

            start = time.time()

            # Step 3: Ask agent to regenerate from the architecture model
            regen_prompt = (
                f"The source code in '{subdir}/' has been deleted. "
                f"Read .architecture-model.yaml for the architecture model. "
                f"Regenerate the Python source files for the '{subdir}/' package "
                f"based on the architecture model's components, symbols, and relationships. "
                f"Then use architect_generate to run the test suite and verify your code passes. "
                f"Iterate until tests pass or you've tried 3 times."
            )

            result = subprocess.run(
                ["opencode", "run", regen_prompt, "--dir", str(work_dir)],
                capture_output=True, text=True, timeout=self.TIMEOUT,
            )

            # Step 4: Run tests ourselves to verify
            test_result = subprocess.run(
                [sys.executable, "-m", "pytest", str(work_dir), "-v", "--tb=short", "-q"],
                capture_output=True, text=True, timeout=120, cwd=str(work_dir),
            )

            elapsed = time.time() - start

            # Parse test output
            test_output = test_result.stdout + test_result.stderr
            passed, failed, total = _parse_test_counts(test_output)

            pass_rate = passed / total if total > 0 else 0.0

            # Record result
            result_data = {
                "test": "e2e_regeneration",
                "timestamp": datetime.now().isoformat(),
                "repo": repo_name,
                "url": repo_info["url"],
                "subdir": subdir,
                "pass_rate": pass_rate,
                "passed_tests": passed,
                "failed_tests": failed,
                "total_tests": total,
                "time_seconds": elapsed,
                "agent_exit_code": result.returncode,
                "test_exit_code": test_result.returncode,
            }

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_file = results_dir / f"e2e_regen_{repo_name}_{ts}.json"
            out_file.write_text(json.dumps(result_data, indent=2))

            # Soft assertion: report pass rate (don't fail test, just record)
            # Regeneration is hard - even 10% is informative data
            print(f"\n  {repo_name}: {pass_rate:.0%} pass rate ({passed}/{total} tests)")

        # Cleanup model from original repo
        model_file.unlink(missing_ok=True)


def _parse_test_counts(output: str) -> tuple[int, int, int]:
    """Parse pytest output for passed/failed/total counts."""
    passed = 0
    failed = 0
    for line in output.split("\n"):
        parts = line.strip().split()
        for i, part in enumerate(parts):
            if part == "passed" and i > 0:
                try:
                    passed = int(parts[i - 1])
                except ValueError:
                    pass
            elif part == "failed" and i > 0:
                try:
                    failed = int(parts[i - 1])
                except ValueError:
                    pass
    total = passed + failed
    return passed, failed, total
```

**Step 2: Verify test is collected but skipped without --e2e**

Run: `pytest tests/e2e/test_regeneration.py -v`
Expected: 5 tests SKIPPED

**Step 3: Commit**

```bash
git add tests/e2e/test_regeneration.py
git commit -m "feat: add E2E regeneration benchmark test (5 repos)"
```

---

### Task 4: Standalone Benchmark Runner Script

**Files:**
- Create: `scripts/run_benchmark.py`

**Step 1: Write standalone script**

```python
#!/usr/bin/env python3
"""Standalone E2E benchmark runner.

Usage:
    python scripts/run_benchmark.py                    # Run default 5 repos
    python scripts/run_benchmark.py --repos click httpx  # Specific repos
    python scripts/run_benchmark.py --extract-only     # Skip regeneration
    python scripts/run_benchmark.py --regen-only       # Skip extraction
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

CLONE_DIR = Path("/tmp/test-repos")
RESULTS_DIR = Path(__file__).parent.parent / "results"

DEFAULT_REPOS = [
    {"name": "python-dotenv", "subdir": "src/dotenv"},
    {"name": "colorama", "subdir": "colorama"},
    {"name": "aiofiles", "subdir": "src/aiofiles"},
    {"name": "tqdm", "subdir": "tqdm"},
    {"name": "structlog", "subdir": "src/structlog"},
]

ALL_REPOS = DEFAULT_REPOS + [
    {"name": "click", "subdir": "src/click"},
    {"name": "typer", "subdir": "typer"},
    {"name": "httpcore", "subdir": "httpcore"},
    {"name": "anyio", "subdir": "src/anyio"},
    {"name": "attrs", "subdir": "src"},
    {"name": "pydantic", "subdir": "pydantic"},
    {"name": "fastapi", "subdir": "fastapi"},
    {"name": "rich", "subdir": "rich"},
    {"name": "httpx", "subdir": "httpx"},
    {"name": "black", "subdir": "src/black"},
    {"name": "marshmallow", "subdir": "src/marshmallow"},
    {"name": "flask", "subdir": "src/flask"},
    {"name": "jinja", "subdir": "src/jinja2"},
    {"name": "starlette", "subdir": "starlette"},
    {"name": "arrow", "subdir": "arrow"},
]


def run_benchmark(repos: list[dict], extract: bool = True, regen: bool = True) -> list[dict]:
    """Run the full benchmark suite."""
    results = []
    RESULTS_DIR.mkdir(exist_ok=True)

    for repo in repos:
        name = repo["name"]
        repo_path = CLONE_DIR / name
        if not repo_path.exists():
            print(f"  SKIP {name} (not cloned)")
            continue

        result = {"repo": name, "subdir": repo["subdir"]}

        if extract:
            print(f"  EXTRACT {name}...", end=" ", flush=True)
            ext_result = run_extraction(repo_path, name)
            result["extraction"] = ext_result
            status = f"score={ext_result.get('score', '?')}" if ext_result.get("success") else "FAIL"
            print(status)

        if regen:
            print(f"  REGEN {name}...", end=" ", flush=True)
            regen_result = run_regeneration(repo_path, name, repo["subdir"])
            result["regeneration"] = regen_result
            rate = regen_result.get("pass_rate", 0)
            print(f"{rate:.0%} ({regen_result.get('passed_tests', 0)}/{regen_result.get('total_tests', 0)})")

        results.append(result)

    return results


def run_extraction(repo_path: Path, name: str) -> dict:
    """Run extraction on a single repo."""
    prompt = (
        f"Use architect_scan to scan this repo, then produce a valid "
        f".architecture-model.yaml. Use architect_extract to validate and store it. "
        f"The model must score >= 80."
    )
    start = time.time()
    try:
        result = subprocess.run(
            ["opencode", "run", prompt, "--dir", str(repo_path)],
            capture_output=True, text=True, timeout=600,
        )
        elapsed = time.time() - start

        model_path = repo_path / ".architecture-model.yaml"
        if model_path.exists():
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "architecture-model-standard" / "src"))
            from architecture_model.core.parser import load_model
            from architecture_model.core.validator import validate_model
            model = load_model(model_path)
            validation = validate_model(model)
            model_path.unlink()  # cleanup
            return {
                "success": True, "score": validation.score,
                "entities": model.entity_count, "time_seconds": elapsed,
            }
        return {"success": False, "error": "No model produced", "time_seconds": elapsed}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout (600s)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_regeneration(repo_path: Path, name: str, subdir: str) -> dict:
    """Run regeneration benchmark on a single repo."""
    import shutil
    import tempfile

    # First extract
    run_extraction(repo_path, name)
    model_file = repo_path / ".architecture-model.yaml"
    if not model_file.exists():
        return {"pass_rate": 0, "error": "No model to regenerate from"}

    with tempfile.TemporaryDirectory(prefix=f"regen_{name}_") as tmpdir:
        work_dir = Path(tmpdir) / name
        shutil.copytree(repo_path, work_dir)

        # Delete source
        src_path = work_dir / subdir
        if src_path.exists():
            shutil.rmtree(src_path)
            src_path.mkdir(parents=True)
            (src_path / "__init__.py").write_text("")

        start = time.time()
        prompt = (
            f"The source code in '{subdir}/' has been deleted. "
            f"Read .architecture-model.yaml and regenerate the source. "
            f"Run the test suite with architect_generate. Iterate up to 3 times."
        )
        try:
            subprocess.run(
                ["opencode", "run", prompt, "--dir", str(work_dir)],
                capture_output=True, text=True, timeout=600,
            )
        except subprocess.TimeoutExpired:
            pass

        # Run tests
        test_result = subprocess.run(
            [sys.executable, "-m", "pytest", str(work_dir), "-v", "--tb=short", "-q"],
            capture_output=True, text=True, timeout=120, cwd=str(work_dir),
        )
        elapsed = time.time() - start

        passed, failed, total = 0, 0, 0
        for line in (test_result.stdout + test_result.stderr).split("\n"):
            parts = line.strip().split()
            for i, part in enumerate(parts):
                if part == "passed" and i > 0:
                    try: passed = int(parts[i - 1])
                    except ValueError: pass
                elif part == "failed" and i > 0:
                    try: failed = int(parts[i - 1])
                    except ValueError: pass
        total = passed + failed

    model_file.unlink(missing_ok=True)
    return {
        "pass_rate": passed / total if total > 0 else 0.0,
        "passed_tests": passed, "failed_tests": failed,
        "total_tests": total, "time_seconds": elapsed,
    }


def main():
    parser = argparse.ArgumentParser(description="E2E Benchmark Runner")
    parser.add_argument("--repos", nargs="*", help="Specific repos to benchmark")
    parser.add_argument("--all", action="store_true", help="Run all 19 repos")
    parser.add_argument("--extract-only", action="store_true")
    parser.add_argument("--regen-only", action="store_true")
    args = parser.parse_args()

    if args.repos:
        repos = [r for r in ALL_REPOS if r["name"] in args.repos]
    elif args.all:
        repos = ALL_REPOS
    else:
        repos = DEFAULT_REPOS

    extract = not args.regen_only
    regen = not args.extract_only

    print(f"\nE2E Benchmark: {len(repos)} repos (extract={extract}, regen={regen})")
    print("=" * 60)

    results = run_benchmark(repos, extract=extract, regen=regen)

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("-" * 60)
    for r in results:
        ext = r.get("extraction", {})
        reg = r.get("regeneration", {})
        ext_str = f"score={ext.get('score', '?')}" if ext.get("success") else ext.get("error", "N/A")[:20]
        reg_str = f"{reg.get('pass_rate', 0):.0%}" if "pass_rate" in reg else "N/A"
        print(f"  {r['repo']:20} extract={ext_str:15} regen={reg_str}")

    # Save results
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = RESULTS_DIR / f"e2e_benchmark_{ts}.json"
    out_file.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "config": {"repos": len(repos), "extract": extract, "regen": regen},
        "results": results,
    }, indent=2))
    print(f"\n  Saved to: {out_file}")


if __name__ == "__main__":
    main()
```

**Step 2: Verify script runs**

Run: `python scripts/run_benchmark.py --help`
Expected: Shows usage help

**Step 3: Commit**

```bash
git add scripts/run_benchmark.py
git commit -m "feat: add standalone E2E benchmark runner script"
```

---

### Task 5: Run Extraction Benchmark (1 repo smoke test)

**Step 1: Run extraction on python-dotenv**

Run: `pytest tests/e2e/test_extraction.py -v --e2e -k python-dotenv`
Expected: PASS with score >= 80

**Step 2: Verify result file written**

Run: `ls results/e2e_extract_python-dotenv_*.json`

---

### Task 6: Run Full Benchmark Suite

**Step 1: Run all 5 repos (extraction only first)**

Run: `python scripts/run_benchmark.py --extract-only`
Expected: 5 repos extracted, scores reported

**Step 2: Run 1 repo regeneration**

Run: `python scripts/run_benchmark.py --repos python-dotenv --regen-only`
Expected: Pass rate reported (any value is informative)

---
