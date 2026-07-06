"""CLI entry point for opencode-arch."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="opencode-arch",
        description="Architecture extraction, generation, and benchmarking CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # extract
    extract_p = subparsers.add_parser("extract", help="Extract architecture from a repository")
    extract_p.add_argument("repo_path", help="Path to the target repository")
    extract_p.add_argument("--budget", type=int, default=4000, help="Token budget (default: 4000)")
    extract_p.add_argument("--focus", default="all", help="Focus: all, F-block ID, layer name")
    extract_p.add_argument("--target-score", type=int, default=80, help="Min validation score (default: 80)")
    extract_p.add_argument("--model", default=None, help="Model override (provider/model)")
    extract_p.add_argument("--timeout", type=int, default=600, help="Timeout seconds (default: 600)")

    # generate
    gen_p = subparsers.add_parser("generate", help="Generate code and run tests")
    gen_p.add_argument("repo_path", help="Path to the target repository")
    gen_p.add_argument("--max-iter", type=int, default=3, help="Max retries (default: 3)")
    gen_p.add_argument("--test-command", default=None, help="Custom test command")
    gen_p.add_argument("--model", default=None, help="Model override (provider/model)")
    gen_p.add_argument("--timeout", type=int, default=600, help="Timeout seconds (default: 600)")

    # bench
    bench_p = subparsers.add_parser("bench", help="Benchmark extraction on multiple repos")
    bench_p.add_argument("repos", nargs="+", help="Paths to target repositories")
    bench_p.add_argument("--output", default=None, help="Output file (JSON)")
    bench_p.add_argument("--model", default=None, help="Model override (provider/model)")

    # metrics
    metrics_p = subparsers.add_parser("metrics", help="Display recorded metrics")
    metrics_p.add_argument("--tool", default=None, help="Filter by tool name")
    metrics_p.add_argument("--last", type=int, default=10, help="Number of records (default: 10)")

    args = parser.parse_args()

    if args.command == "extract":
        from opencode_arch.cli.extract import run_extract
        from opencode_arch.runner.opencode import OpencodeRunner
        runner = OpencodeRunner(timeout=args.timeout, model=args.model)
        result = asyncio.run(run_extract(
            repo_path=args.repo_path, runner=runner,
            budget=args.budget, focus=args.focus, target_score=args.target_score,
        ))
        _print_extract_result(result)

    elif args.command == "generate":
        from opencode_arch.cli.generate import run_generate
        from opencode_arch.runner.opencode import OpencodeRunner
        runner = OpencodeRunner(timeout=args.timeout, model=args.model)
        result = asyncio.run(run_generate(
            repo_path=args.repo_path, runner=runner,
            max_iter=args.max_iter, test_command=args.test_command,
        ))
        _print_generate_result(result)

    elif args.command == "bench":
        from opencode_arch.cli.bench import run_bench
        from opencode_arch.runner.opencode import OpencodeRunner
        runner = OpencodeRunner(model=args.model)
        results = asyncio.run(run_bench(repos=args.repos, runner=runner))
        _print_bench_results(results, output_file=args.output)

    elif args.command == "metrics":
        from opencode_arch.cli.metrics import show_metrics
        show_metrics(tool=args.tool, last=args.last)


def _print_extract_result(result: dict):
    if result.get("success"):
        print("Extraction successful!")
        print(f"  Score:   {result['score']}/100")
        print(f"  Tokens:  {result['tokens_used']}")
        print(f"  Time:    {result['time_seconds']:.1f}s")
        print(f"  Path:    {result.get('path', 'N/A')}")
        if result.get("issues"):
            print(f"  Issues:  {len(result['issues'])}")
    else:
        print(f"Extraction failed: {result.get('error', 'unknown')}")
        sys.exit(1)


def _print_generate_result(result: dict):
    if result.get("passed"):
        print("Code generation successful!")
        print(f"  Pass rate:   {result['pass_rate']:.0%}")
        print(f"  Tests:       {result['total_tests']}")
        print(f"  Iterations:  {result['iterations']}")
        print(f"  Time:        {result['time_seconds']:.1f}s")
    else:
        print("Code generation incomplete")
        print(f"  Pass rate:   {result.get('pass_rate', 0):.0%}")
        if result.get("error"):
            print(f"  Error:       {result['error']}")
        sys.exit(1)


def _print_bench_results(results: list[dict], output_file: str | None):
    import json
    print(f"\nBenchmark Results ({len(results)} repos)")
    print("-" * 60)
    for r in results:
        status = "PASS" if r.get("success") else "FAIL"
        print(f"  [{status}] {r.get('repo', '?'):30} score={r.get('score', 0):3} time={r.get('time_seconds', 0):.1f}s")
    scores = [r["score"] for r in results if r.get("success")]
    if scores:
        print(f"\n  Average score: {sum(scores)/len(scores):.0f}/100")
        print(f"  Success rate:  {len(scores)}/{len(results)}")
    if output_file:
        Path(output_file).write_text(json.dumps(results, indent=2))
        print(f"\n  Saved to: {output_file}")


if __name__ == "__main__":
    main()
