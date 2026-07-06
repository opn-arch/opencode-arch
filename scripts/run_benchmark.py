#!/usr/bin/env python3
"""Standalone E2E benchmark runner.

Usage:
    python scripts/run_benchmark.py                      # Run default 5 repos (extract only)
    python scripts/run_benchmark.py --repos click httpx  # Specific repos
    python scripts/run_benchmark.py --extract-only       # Skip regeneration
    python scripts/run_benchmark.py --regen-only         # Skip extraction
    python scripts/run_benchmark.py --all                # Run all 19 repos
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
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


def run_extraction(repo_path: Path, name: str) -> dict:
    """Run extraction on a single repo via opencode run."""
    prompt = (
        f"Use architect_scan to scan this repo, then produce a valid "
        f".architecture-model.yaml. Use architect_extract to validate and store it. "
        f"The model must score >= 80. Include meta (project: {name}, "
        f"schema_version: '1.3'), entities (capabilities, components), "
        f"and relationships (realizes, depends-on, contains)."
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
            # Add src to path for architecture_model imports
            ams_src = Path(__file__).parent.parent.parent / "architecture-model-standard" / "src"
            if str(ams_src) not in sys.path:
                sys.path.insert(0, str(ams_src))

            from architecture_model.core.parser import load_model
            from architecture_model.core.validator import validate_model

            model = load_model(model_path)
            validation = validate_model(model)
            score = validation.score
            entities = model.entity_count
            relationships = len(model.relationships)
            issues = [str(i) for i in validation.issues[:5]]
            # Don't delete — regeneration may need it
            return {
                "success": True, "score": score,
                "entities": entities, "relationships": relationships,
                "issues": issues, "time_seconds": elapsed,
            }
        return {"success": False, "error": "No model produced", "time_seconds": elapsed}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout (600s)", "time_seconds": 600}
    except Exception as e:
        return {"success": False, "error": str(e), "time_seconds": time.time() - start}


def run_regeneration(repo_path: Path, name: str, subdir: str) -> dict:
    """Run regeneration benchmark: delete source, regenerate, run tests."""
    model_file = repo_path / ".architecture-model.yaml"
    if not model_file.exists():
        # Need to extract first
        print(f"    (extracting model first...)", flush=True)
        ext = run_extraction(repo_path, name)
        if not ext.get("success"):
            return {"pass_rate": 0, "error": "No model to regenerate from", "total_tests": 0}

    with tempfile.TemporaryDirectory(prefix=f"regen_{name}_") as tmpdir:
        work_dir = Path(tmpdir) / name
        shutil.copytree(repo_path, work_dir)

        # Delete source directory
        src_path = work_dir / subdir
        if src_path.exists():
            shutil.rmtree(src_path)
            src_path.mkdir(parents=True)
            (src_path / "__init__.py").write_text("")

        start = time.time()
        prompt = (
            f"The source code in '{subdir}/' has been deleted. "
            f"Read .architecture-model.yaml for the architecture model. "
            f"Regenerate the Python source files for the '{subdir}/' package "
            f"based on the architecture model's components, symbols, and relationships. "
            f"Then use architect_generate to run the test suite and verify your code passes. "
            f"Iterate until tests pass or you've tried 3 times."
        )
        try:
            subprocess.run(
                ["opencode", "run", prompt, "--dir", str(work_dir)],
                capture_output=True, text=True, timeout=600,
            )
        except subprocess.TimeoutExpired:
            pass

        # Run tests ourselves to verify
        try:
            test_result = subprocess.run(
                [sys.executable, "-m", "pytest", str(work_dir), "-v", "--tb=short", "-q"],
                capture_output=True, text=True, timeout=120, cwd=str(work_dir),
            )
            test_output = test_result.stdout + test_result.stderr
        except subprocess.TimeoutExpired:
            test_output = ""
        except Exception:
            test_output = ""

        elapsed = time.time() - start
        passed, failed, total = _parse_test_counts(test_output)

    # Cleanup model from original repo
    model_file.unlink(missing_ok=True)

    return {
        "pass_rate": passed / total if total > 0 else 0.0,
        "passed_tests": passed, "failed_tests": failed,
        "total_tests": total, "time_seconds": elapsed,
    }


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


def run_benchmark(repos: list[dict], extract: bool = True, regen: bool = True) -> list[dict]:
    """Run the full benchmark suite."""
    RESULTS_DIR.mkdir(exist_ok=True)
    results = []

    for repo in repos:
        name = repo["name"]
        repo_path = CLONE_DIR / name
        if not repo_path.exists():
            print(f"  SKIP {name} (not cloned at {repo_path})")
            continue

        result = {"repo": name, "subdir": repo["subdir"]}

        if extract:
            print(f"  EXTRACT {name}...", end=" ", flush=True)
            ext_result = run_extraction(repo_path, name)
            result["extraction"] = ext_result
            if ext_result.get("success"):
                print(f"score={ext_result['score']} entities={ext_result['entities']} "
                      f"rels={ext_result['relationships']} ({ext_result['time_seconds']:.0f}s)")
            else:
                print(f"FAIL: {ext_result.get('error', '?')[:50]}")

        if regen:
            print(f"  REGEN  {name}...", end=" ", flush=True)
            regen_result = run_regeneration(repo_path, name, repo["subdir"])
            result["regeneration"] = regen_result
            rate = regen_result.get("pass_rate", 0)
            total = regen_result.get("total_tests", 0)
            passed = regen_result.get("passed_tests", 0)
            print(f"{rate:.0%} ({passed}/{total} tests, {regen_result.get('time_seconds', 0):.0f}s)")

        results.append(result)

    return results


def main():
    parser = argparse.ArgumentParser(
        prog="run_benchmark",
        description="E2E Benchmark Runner — tests extraction + regeneration on real repos",
    )
    parser.add_argument("--repos", nargs="*", help="Specific repos to benchmark")
    parser.add_argument("--all", action="store_true", help="Run all 19 repos")
    parser.add_argument("--extract-only", action="store_true", help="Skip regeneration")
    parser.add_argument("--regen-only", action="store_true", help="Skip extraction")
    args = parser.parse_args()

    if args.repos:
        repos = [r for r in ALL_REPOS if r["name"] in args.repos]
        if not repos:
            print(f"ERROR: No matching repos. Available: {[r['name'] for r in ALL_REPOS]}")
            sys.exit(1)
    elif args.all:
        repos = ALL_REPOS
    else:
        repos = DEFAULT_REPOS

    extract = not args.regen_only
    regen = not args.extract_only

    print(f"\nE2E Benchmark: {len(repos)} repos (extract={extract}, regen={regen})")
    print("=" * 70)

    results = run_benchmark(repos, extract=extract, regen=regen)

    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("-" * 70)
    print(f"  {'Repo':<20} {'Extraction':<25} {'Regeneration':<20}")
    print(f"  {'-'*20} {'-'*25} {'-'*20}")
    for r in results:
        ext = r.get("extraction", {})
        reg = r.get("regeneration", {})
        if ext.get("success"):
            ext_str = f"score={ext['score']} ({ext['entities']}e/{ext['relationships']}r)"
        elif ext:
            ext_str = f"FAIL: {ext.get('error', '?')[:15]}"
        else:
            ext_str = "N/A"
        if "pass_rate" in reg:
            reg_str = f"{reg['pass_rate']:.0%} ({reg['passed_tests']}/{reg['total_tests']})"
        else:
            reg_str = "N/A"
        print(f"  {r['repo']:<20} {ext_str:<25} {reg_str:<20}")

    # Aggregate stats
    ext_scores = [r["extraction"]["score"] for r in results if r.get("extraction", {}).get("success")]
    reg_rates = [r["regeneration"]["pass_rate"] for r in results if "pass_rate" in r.get("regeneration", {})]

    if ext_scores:
        print(f"\n  Extraction:    avg score = {sum(ext_scores)/len(ext_scores):.0f}/100 "
              f"({len(ext_scores)}/{len(results)} succeeded)")
    if reg_rates:
        print(f"  Regeneration:  avg pass rate = {sum(reg_rates)/len(reg_rates):.0%} "
              f"({len(reg_rates)} repos)")

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
