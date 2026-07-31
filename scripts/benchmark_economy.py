#!/usr/bin/env python3
"""Benchmark opencode-arch: accuracy, economy, and regen overhead.

Runs the blind regen loop on 5 new repos and reports:
- Blind first-iteration accuracy (pass rate before any feedback)
- Compression ratio (source_equivalent / prompt_tokens)
- Regen overhead (extra tokens from iterations > 1)
- Total LLM cost vs naive cost (reading raw source)
- Convergence rate (% subsystems reaching target)

Usage:
    python scripts/benchmark_economy.py                    # Run 5 new repos
    python scripts/benchmark_economy.py --repos httpx rich # Specific repos
    python scripts/benchmark_economy.py --dry-run          # Show plan without running
    python scripts/benchmark_economy.py --report-only      # Report from existing telemetry
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path
SRC_DIR = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

# Also add architecture-model-standard
AMS_DIR = Path(__file__).parent.parent.parent / "architecture-model-standard" / "src"
if AMS_DIR.exists():
    sys.path.insert(0, str(AMS_DIR))

CLONE_DIR = Path("/tmp/bench-repos")
RESULTS_DIR = Path(__file__).parent.parent / "results"
PROJECT_DIR = Path(__file__).parent.parent.parent / "architecture-model-standard"

# 5 benchmark repos (fresh clones with tests)
BENCHMARK_REPOS = [
    {"name": "click", "subdir": "src/click"},
    {"name": "structlog", "subdir": "src/structlog"},
    {"name": "httpx", "subdir": "httpx"},
    {"name": "marshmallow", "subdir": "src/marshmallow"},
    {"name": "arrow", "subdir": "arrow"},
]

# Hard repos - monoliths, multi-language, large codebases
HARD_REPOS = [
    {"name": "pydantic", "subdir": "pydantic"},
    {"name": "black", "subdir": "src/black"},
    {"name": "celery", "subdir": "celery"},
    {"name": "sqlalchemy", "subdir": "lib/sqlalchemy"},
    {"name": "django", "subdir": "django"},
]


def ensure_extraction(repo_path: Path, name: str, timeout: int = 600) -> bool:
    """Ensure .architecture-model.yaml exists for the repo (extract if needed)."""
    model_file = repo_path / ".architecture-model.yaml"
    if model_file.exists():
        return True

    print(f"    Extracting architecture model for {name} (timeout={timeout}s)...", flush=True)
    prompt = (
        f"Use architect_scan to scan the repository at {repo_path}, then produce a valid "
        f".architecture-model.yaml in that directory. Use architect_extract to validate "
        f"and store it. The model must score >= 80. Include meta (project: {name}, "
        f"schema_version: '1.3'), entities (capabilities, components with signatures, "
        f"constants, symbols, and files), and relationships."
    )
    try:
        subprocess.run(
            ["opencode", "run", prompt, "--dir", str(PROJECT_DIR),
             "--dangerously-skip-permissions"],
            capture_output=True, text=True, timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"    FAILED: {e}", flush=True)
        return False

    return model_file.exists()


async def run_regen_benchmark(
    repo_path: Path,
    name: str,
    max_iterations: int = 5,
    target_pass_rate: float = 1.0,
    timeout: int = 600,
) -> dict[str, Any]:
    """Run blind regen loop on a repo and return structured metrics."""
    from opencode_arch.cli.regen_loop import run_regen_loop
    from opencode_arch.runner.opencode import OpencodeRunner

    runner = OpencodeRunner(timeout=timeout)

    start = time.time()
    result = await run_regen_loop(
        repo_path=repo_path,
        runner=runner,
        max_iterations=max_iterations,
        target_pass_rate=target_pass_rate,
        blind=True,
    )
    elapsed = time.time() - start

    result["total_time"] = elapsed
    result["repo_name"] = name
    return result


def query_telemetry_for_repo(repo_name: str) -> dict[str, Any]:
    """Query telemetry DB for per-subsystem metrics of a repo."""
    from opencode_arch.telemetry.store import TelemetryStore

    import sqlite3
    store = TelemetryStore()
    conn = sqlite3.connect(store.db_path)

    # Get all blind runs, then in Python keep only the latest run per subsystem
    all_rows = conn.execute(
        """SELECT subsystem, iteration, pass_rate, prompt_tokens,
                  source_equivalent_tokens, compression_ratio, mode, id
           FROM regen_outcomes
           WHERE repo = ? AND mode = 'blind'
           ORDER BY subsystem, id""",
        (repo_name,),
    ).fetchall()

    # Keep only the latest run: for each subsystem, take the last contiguous
    # sequence of iterations (the run with the highest IDs)
    from itertools import groupby
    rows = []
    for sub_name, group in groupby(all_rows, key=lambda r: r[0]):
        entries = list(group)
        # Find where the last run starts (iteration resets to 1)
        last_run_start = 0
        for i, e in enumerate(entries):
            if e[1] == 1:  # iteration == 1 means new run
                last_run_start = i
        rows.extend(entries[last_run_start:])
    conn.close()

    if not rows:
        return {"subsystems": [], "summary": {}}

    # Group by subsystem
    subsystems: dict[str, list] = {}
    for row in rows:
        sub_name = row[0]
        if sub_name not in subsystems:
            subsystems[sub_name] = []
        subsystems[sub_name].append({
            "iteration": row[1],
            "pass_rate": row[2],
            "prompt_tokens": row[3],
            "source_equivalent_tokens": row[4],
            "compression_ratio": row[5],
        })

    # Compute per-subsystem metrics
    sub_metrics = []
    for sub_name, iters in subsystems.items():
        first_iter = iters[0] if iters else {}
        last_iter = iters[-1] if iters else {}
        total_prompt = sum(i["prompt_tokens"] for i in iters)

        sub_metrics.append({
            "name": sub_name,
            "first_iter_pass_rate": first_iter.get("pass_rate", 0),
            "final_pass_rate": last_iter.get("pass_rate", 0),
            "iterations": len(iters),
            "prompt_tokens_first": first_iter.get("prompt_tokens", 0),
            "prompt_tokens_total": total_prompt,
            "source_equivalent": first_iter.get("source_equivalent_tokens", 0),
            "compression_ratio": first_iter.get("compression_ratio", 0),
            "converged": last_iter.get("pass_rate", 0) >= 1.0,
        })

    # Summary
    n = len(sub_metrics)
    first_iter_rates = [s["first_iter_pass_rate"] for s in sub_metrics]
    perfect_first = sum(1 for r in first_iter_rates if r >= 1.0)
    total_prompt_all = sum(s["prompt_tokens_total"] for s in sub_metrics)
    total_source_eq = sum(s["source_equivalent"] for s in sub_metrics)
    first_only_cost = sum(s["prompt_tokens_first"] for s in sub_metrics)
    regen_overhead = total_prompt_all - first_only_cost
    converged = sum(1 for s in sub_metrics if s["converged"])

    summary = {
        "total_subsystems": n,
        "avg_first_iter_accuracy": sum(first_iter_rates) / n if n else 0,
        "perfect_first_try": perfect_first,
        "converged": converged,
        "avg_compression_ratio": sum(s["compression_ratio"] for s in sub_metrics) / n if n else 0,
        "total_prompt_tokens": total_prompt_all,
        "total_source_equivalent": total_source_eq,
        "overall_compression": total_source_eq / total_prompt_all if total_prompt_all else 0,
        "regen_overhead_tokens": regen_overhead,
        "regen_overhead_pct": regen_overhead / total_prompt_all * 100 if total_prompt_all else 0,
        "naive_cost_estimate": total_source_eq * (sum(s["iterations"] for s in sub_metrics) / n if n else 1),
    }

    return {"subsystems": sub_metrics, "summary": summary}


def print_report(repos: list[str]):
    """Print formatted benchmark report from telemetry data."""
    print("\n" + "=" * 100)
    print("OPENCODE-ARCH BENCHMARK: ACCURACY & ECONOMY REPORT")
    print("=" * 100)

    all_summaries = []

    for repo_name in repos:
        data = query_telemetry_for_repo(repo_name)
        if not data["subsystems"]:
            print(f"\n  {repo_name}: NO DATA")
            continue

        summary = data["summary"]
        all_summaries.append({"repo": repo_name, **summary})

        # Per-repo detail
        print(f"\n{'─' * 100}")
        print(f"  {repo_name.upper()} ({summary['total_subsystems']} subsystems)")
        print(f"{'─' * 100}")

        # Subsystem table
        print(f"  {'Subsystem':<20} {'1st Pass%':<10} {'Final%':<8} {'Iters':<6} "
              f"{'Prompt':<8} {'Baseline':<10} {'Comp.':<8} {'Conv.':<6}")
        print(f"  {'─'*20} {'─'*10} {'─'*8} {'─'*6} {'─'*8} {'─'*10} {'─'*8} {'─'*6}")

        for s in sorted(data["subsystems"], key=lambda x: x["name"]):
            conv_mark = "YES" if s["converged"] else "no"
            print(f"  {s['name']:<20} {s['first_iter_pass_rate']:>7.0%}   "
                  f"{s['final_pass_rate']:>5.0%}   {s['iterations']:>3}   "
                  f"{s['prompt_tokens_first']:>6}  {s['source_equivalent']:>8}  "
                  f"{s['compression_ratio']:>6.1f}x  {conv_mark:<6}")

        # Per-repo summary
        print(f"\n  Summary:")
        print(f"    1st-iteration accuracy: {summary['avg_first_iter_accuracy']:.1%} "
              f"(perfect on first try: {summary['perfect_first_try']}/{summary['total_subsystems']})")
        print(f"    Convergence rate:       {summary['converged']}/{summary['total_subsystems']}")
        print(f"    Avg compression:        {summary['avg_compression_ratio']:.1f}x")
        print(f"    Total LLM cost:         {summary['total_prompt_tokens']:,} tokens")
        print(f"    Naive cost (no tool):   {summary['total_source_equivalent']:,} tokens")
        print(f"    Overall savings:        {summary['overall_compression']:.1f}x")
        print(f"    Regen overhead:         {summary['regen_overhead_tokens']:,} tokens "
              f"({summary['regen_overhead_pct']:.1f}% of total)")

    # Grand summary
    if all_summaries:
        print(f"\n{'═' * 100}")
        print("GRAND SUMMARY")
        print(f"{'═' * 100}")

        n = len(all_summaries)
        print(f"\n  {'Repo':<15} {'Subs':<6} {'1st Accuracy':<14} {'Converge':<10} "
              f"{'Compression':<12} {'LLM Cost':<10} {'Naive Cost':<12} {'Savings':<8} {'Regen OH':<10}")
        print(f"  {'─'*15} {'─'*6} {'─'*14} {'─'*10} {'─'*12} {'─'*10} {'─'*12} {'─'*8} {'─'*10}")

        total_llm = 0
        total_naive = 0
        total_regen = 0

        for s in all_summaries:
            savings_x = s["overall_compression"]
            print(f"  {s['repo']:<15} {s['total_subsystems']:<6} "
                  f"{s['avg_first_iter_accuracy']:>10.1%}    "
                  f"{s['converged']}/{s['total_subsystems']:<6}  "
                  f"{s['avg_compression_ratio']:>8.1f}x   "
                  f"{s['total_prompt_tokens']:>8,}  "
                  f"{s['total_source_equivalent']:>10,}  "
                  f"{savings_x:>5.1f}x   "
                  f"{s['regen_overhead_pct']:>6.1f}%")
            total_llm += s["total_prompt_tokens"]
            total_naive += s["total_source_equivalent"]
            total_regen += s["regen_overhead_tokens"]

        print(f"  {'─'*15} {'─'*6} {'─'*14} {'─'*10} {'─'*12} {'─'*10} {'─'*12} {'─'*8} {'─'*10}")

        avg_accuracy = sum(s["avg_first_iter_accuracy"] for s in all_summaries) / n
        overall_savings = total_naive / total_llm if total_llm else 0
        regen_pct = total_regen / total_llm * 100 if total_llm else 0

        print(f"  {'TOTAL':<15} {sum(s['total_subsystems'] for s in all_summaries):<6} "
              f"{avg_accuracy:>10.1%}    "
              f"{'':>10} {'':>12} "
              f"{total_llm:>8,}  {total_naive:>10,}  "
              f"{overall_savings:>5.1f}x   {regen_pct:>6.1f}%")

        print(f"\n  KEY FINDINGS:")
        print(f"    - Blind first-iteration accuracy: {avg_accuracy:.1%}")
        print(f"    - Overall token savings: {overall_savings:.1f}x (tool cost vs reading raw source)")
        print(f"    - Regen overhead: {regen_pct:.1f}% of total LLM spend goes to V&V iterations")
        print(f"    - Total LLM cost: {total_llm:,} tokens for {sum(s['total_subsystems'] for s in all_summaries)} subsystems")
        print(f"    - Without tool: {total_naive:,} tokens would be needed (reading source + deps)")


async def run_all(repos_to_run: list[dict], max_iterations: int, target: float, timeout: int):
    """Run benchmark on all specified repos sequentially."""
    RESULTS_DIR.mkdir(exist_ok=True)

    for repo_info in repos_to_run:
        name = repo_info["name"]
        repo_path = CLONE_DIR / name

        if not repo_path.exists():
            print(f"\n  SKIP {name}: not cloned at {repo_path}")
            continue

        print(f"\n{'━' * 60}")
        print(f"  BENCHMARKING: {name}")
        print(f"{'━' * 60}")

        # Step 1: Ensure architecture model exists
        if not ensure_extraction(repo_path, name, timeout=timeout):
            print(f"    FAILED: Could not extract architecture model")
            continue

        # Step 2: Run blind regen loop
        print(f"    Running blind regen loop (max_iter={max_iterations}, target={target:.0%})...")
        result = await run_regen_benchmark(
            repo_path=repo_path,
            name=name,
            max_iterations=max_iterations,
            target_pass_rate=target,
            timeout=timeout,
        )

        if result.get("success"):
            sub_results = result.get("subsystem_results", {})
            converged = result.get("converged_subsystems", 0)
            total = result.get("total_subsystems", 0)
            print(f"    Done: {converged}/{total} subsystems converged in {result['total_time']:.0f}s")
        else:
            print(f"    ERROR: {result.get('error', 'unknown')}")

    # Step 3: Report
    repo_names = [r["name"] for r in repos_to_run]
    print_report(repo_names)

    # Step 4: Save results
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = RESULTS_DIR / f"benchmark_economy_{ts}.json"

    # Pull fresh data from telemetry for JSON export
    export_data = {}
    for name in repo_names:
        data = query_telemetry_for_repo(name)
        if data["subsystems"]:
            export_data[name] = data

    out_file.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "config": {
            "repos": repo_names,
            "max_iterations": max_iterations,
            "target_pass_rate": target,
            "mode": "blind",
        },
        "results": export_data,
    }, indent=2))
    print(f"\n  Results saved to: {out_file}")


def main():
    parser = argparse.ArgumentParser(
        prog="benchmark_economy",
        description="Benchmark opencode-arch accuracy, economy & regen overhead",
    )
    parser.add_argument("--repos", nargs="*", help="Specific repos to benchmark")
    parser.add_argument("--hard", action="store_true", help="Run hard repos (large/monolith/multi-lang)")
    parser.add_argument("--max-iterations", type=int, default=5, help="Max iterations per subsystem (default: 5)")
    parser.add_argument("--target", type=float, default=1.0, help="Target pass rate (default: 1.0)")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout per LLM call in seconds (default: 600)")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without running")
    parser.add_argument("--report-only", action="store_true", help="Report from existing telemetry only")
    args = parser.parse_args()

    if args.repos:
        if args.report_only:
            print_report(args.repos)
            return
        all_known = {r["name"]: r for r in BENCHMARK_REPOS + HARD_REPOS}
        repos = [all_known[n] for n in args.repos if n in all_known]
        if not repos:
            available = [r["name"] for r in BENCHMARK_REPOS + HARD_REPOS]
            print(f"ERROR: No matching repos. Available: {available}")
            sys.exit(1)
    elif args.hard:
        repos = HARD_REPOS
        if args.timeout == 600:
            args.timeout = 1200  # auto-increase for hard repos
    else:
        repos = BENCHMARK_REPOS

    if args.report_only:
        repo_names = [r["name"] for r in repos]
        print_report(repo_names)
        return

    if args.dry_run:
        print("\nDRY RUN — would benchmark these repos:")
        print(f"{'─' * 50}")
        for r in repos:
            repo_path = CLONE_DIR / r["name"]
            exists = "EXISTS" if repo_path.exists() else "NOT FOUND"
            model = "HAS MODEL" if (repo_path / ".architecture-model.yaml").exists() else "needs extraction"
            print(f"  {r['name']:<15} {r['subdir']:<20} [{exists}] [{model}]")
        print(f"\nConfig: max_iter={args.max_iterations}, target={args.target:.0%}, "
              f"timeout={args.timeout}s, mode=blind")
        print(f"Estimated time: {len(repos) * 5}-{len(repos) * 15} minutes")
        return

    asyncio.run(run_all(repos, args.max_iterations, args.target, args.timeout))


if __name__ == "__main__":
    main()
