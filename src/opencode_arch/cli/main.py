"""CLI entry point for opencode-arch."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


def main():
    # If no args or first arg looks like a path (not a subcommand), launch interactive
    if len(sys.argv) <= 1 or (
        len(sys.argv) == 2 and not sys.argv[1].startswith("-")
        and sys.argv[1] not in (
            "extract", "generate", "bench", "metrics", "report",
            "regen-loop", "confidence", "calibrate", "export-data", "docs", "export",
            "lifecycle", "ai",
        )
    ):
        from opencode_arch.cli.launch import run_launch
        repo_path = sys.argv[1] if len(sys.argv) == 2 else None
        run_launch(repo_path=repo_path)
        return

    parser = argparse.ArgumentParser(
        prog="opencode-arch",
        description="Architecture-aware development — launch interactive session or run commands",
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
    metrics_p.add_argument("--learning-curve", action="store_true", help="Show learning curve data")
    metrics_p.add_argument("--drift", action="store_true", help="Show documentation drift flags")

    # report
    report_p = subparsers.add_parser("report", help="Display latest report card")
    report_p.add_argument("--repo", default=None, help="Filter by repository name")
    report_p.add_argument("--last", type=int, default=5, help="Number of report cards (default: 5)")

    # regen-loop
    regen_p = subparsers.add_parser("regen-loop", help="Run decomposed regen loop")
    regen_p.add_argument("--repo", required=True, help="Path to the target repository")
    regen_p.add_argument("--max-iterations", type=int, default=5, help="Max iterations per subsystem (default: 5)")
    regen_p.add_argument("--target", type=float, default=0.5, help="Target pass rate (default: 0.5)")
    regen_p.add_argument("--subsystem", default=None, help="Process only this subsystem")
    regen_p.add_argument("--blind", action="store_true", default=False, help="Blind mode: agent only gets model context, no source access")
    regen_p.add_argument("--model", default=None, help="Model override (provider/model)")
    regen_p.add_argument("--timeout", type=int, default=600, help="Timeout seconds per LLM call (default: 600)")

    # confidence
    conf_p = subparsers.add_parser("confidence", help="Show confidence report for extracted model")
    conf_p.add_argument("repo_path", help="Path to the target repository")

    # calibrate
    cal_p = subparsers.add_parser("calibrate", help="Spot-check confidence by attempting regeneration")
    cal_p.add_argument("repo_path", help="Path to the target repository")
    cal_p.add_argument("--n", type=int, default=3, help="Number of components to calibrate (default: 3)")
    cal_p.add_argument("--min-confidence", type=float, default=0.7, help="Min confidence threshold (default: 0.7)")

    # export-data
    export_p = subparsers.add_parser("export-data", help="Export training corpus from .architecture/ artifacts")
    export_p.add_argument("repos", nargs="*", default=["."], help="Paths to repos (default: current dir)")
    export_p.add_argument("--output", "-o", default="corpus.jsonl", help="Output file (default: corpus.jsonl)")
    export_p.add_argument("--include-telemetry", action="store_true", help="Include telemetry DB records")

    # docs (with sub-subcommands: generate, list)
    docs_p = subparsers.add_parser("docs", help="Generate SE documentation")

    # export
    exp_p = subparsers.add_parser("export", help="Export flat files for mobile AI")
    exp_p.add_argument("repo_path", help="Path to the target repository")
    exp_p.add_argument("--output", "-o", default=None, help="Output path (dir or .zip)")
    exp_p.add_argument("--format", choices=["dir", "zip"], default="dir", help="Output format (default: dir)")
    exp_p.add_argument("--prefix", default="", help="File prefix override")
    docs_sub = docs_p.add_subparsers(dest="docs_command", required=True)

    # docs generate
    docs_gen_p = docs_sub.add_parser("generate", help="Generate documentation artifacts")
    docs_gen_p.add_argument("project_path", help="Path to the target project")
    docs_gen_p.add_argument("--output-dir", default=None, help="Output directory (default: docs/se/)")
    docs_gen_p.add_argument("--artifacts", default=None, help="Comma-separated artifact IDs to generate")
    docs_gen_p.add_argument("--model-path", default=None, help="Path to .architecture-model.yaml")
    docs_gen_p.add_argument("--model", default=None, help="Model override (provider/model)")
    docs_gen_p.add_argument("--timeout", type=int, default=600, help="Timeout seconds (default: 600)")

    # docs list
    docs_list_p = docs_sub.add_parser("list", help="List artifacts that would be generated")
    docs_list_p.add_argument("project_path", help="Path to the target project")
    docs_list_p.add_argument("--model-path", default=None, help="Path to .architecture-model.yaml")

    # docs validate
    docs_val_p = docs_sub.add_parser("validate", help="Validate generated documentation")
    docs_val_p.add_argument("project_path", help="Path to the target project")
    docs_val_p.add_argument("--docs-dir", default=None, help="Docs directory (default: docs/se/)")
    docs_val_p.add_argument("--model-path", default=None, help="Path to .architecture-model.yaml")

    from opencode_arch.cli.lifecycle import (
        register_lifecycle_subparsers, register_ai_subparsers,
        dispatch_lifecycle, dispatch_ai,
    )
    register_lifecycle_subparsers(subparsers)
    register_ai_subparsers(subparsers)

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
        show_metrics(
            tool=args.tool,
            last=args.last,
            learning_curve=args.learning_curve,
            drift=args.drift,
        )

    elif args.command == "report":
        from opencode_arch.cli.metrics import show_report
        show_report(repo=args.repo, last=args.last)

    elif args.command == "regen-loop":
        from opencode_arch.cli.regen_loop import run_regen_loop
        from opencode_arch.runner.opencode import OpencodeRunner
        runner = OpencodeRunner(timeout=args.timeout, model=args.model)
        result = asyncio.run(run_regen_loop(
            repo_path=Path(args.repo),
            runner=runner,
            max_iterations=args.max_iterations,
            target_pass_rate=args.target,
            subsystem_name=args.subsystem,
            blind=args.blind,
        ))
        _print_regen_result(result)

    elif args.command == "confidence":
        from opencode_arch.cli.confidence import run_confidence
        output = run_confidence(args.repo_path)
        print(output)

    elif args.command == "calibrate":
        from opencode_arch.cli.calibrate import select_calibration_targets, format_calibration_prompt
        from architecture_model.core.parser import load_model
        from architecture_model.core.confidence import compute_model_confidence
        model_file = Path(args.repo_path) / ".architecture-model.yaml"
        if not model_file.exists():
            model_file = Path(args.repo_path) / ".architecture-model-extracted.yaml"
        if not model_file.exists():
            print("Error: No model found. Run extraction first.")
            sys.exit(1)
        model = load_model(model_file)
        compute_model_confidence(model)
        targets = select_calibration_targets(model, n=args.n, min_confidence=args.min_confidence)
        if not targets:
            print("No calibration targets found.")
            sys.exit(0)
        for comp in targets:
            prompt = format_calibration_prompt(comp)
            print(prompt)
            print()

    elif args.command == "export-data":
        from opencode_arch.cli.export_data import run_export_data
        run_export_data(
            repos=args.repos,
            output=args.output,
            include_telemetry=args.include_telemetry,
        )

    elif args.command == "export":
        from opencode_arch.mcp.tools.export import export_repository
        result = asyncio.run(export_repository(
            repo_path=args.repo_path,
            output_dir=args.output or "",
            output_format=args.format,
            prefix=args.prefix,
        ))
        _print_export_result(result)

    elif args.command == "docs":
        from opencode_arch.cli.docs import run_docs_generate, run_docs_list
        if args.docs_command == "generate":
            from opencode_arch.runner.opencode import OpencodeRunner
            runner = OpencodeRunner(timeout=args.timeout, model=args.model)
            output_dir = Path(args.output_dir) if args.output_dir else None
            artifact_filter = args.artifacts.split(",") if args.artifacts else None
            model_path = Path(args.model_path) if args.model_path else None
            result = asyncio.run(run_docs_generate(
                repo_path=Path(args.project_path),
                runner=runner,
                output_dir=output_dir,
                artifact_filter=artifact_filter,
                model_path=model_path,
            ))
            _print_docs_result(result)
        elif args.docs_command == "list":
            model_path = Path(args.model_path) if args.model_path else None
            artifacts = asyncio.run(run_docs_list(
                repo_path=Path(args.project_path),
                model_path=model_path,
            ))
            _print_docs_list(artifacts)
        elif args.docs_command == "validate":
            from opencode_arch.cli.docs_validator import validate_docs, DocsValidationResult
            from architecture_model import load_model, generate_manifest
            project_path = Path(args.project_path)
            model_path = Path(args.model_path) if args.model_path else project_path / ".architecture-model.yaml"
            docs_dir = Path(args.docs_dir) if args.docs_dir else project_path / "docs" / "se"
            model = load_model(model_path)
            try:
                manifest = generate_manifest(project_path)
            except Exception:
                manifest = None
            result = validate_docs(docs_dir, model, manifest)
            _print_validation_result(result)

    elif args.command == "lifecycle":
        sys.exit(dispatch_lifecycle(args))

    elif args.command == "ai":
        sys.exit(dispatch_ai(args))


def _print_docs_result(result):
    from opencode_arch.cli.docs import DocsResult
    if result.error:
        print(f"Docs generation failed: {result.error}")
        sys.exit(1)
    print(f"\nDocs Generation Complete")
    print(f"  Output:    {result.output_dir}")
    print(f"  Generated: {len(result.generated)} artifacts")
    if result.failed:
        print(f"  Failed:    {len(result.failed)} ({', '.join(result.failed)})")
    print(f"  Time:      {result.time_seconds:.1f}s")


def _print_docs_list(artifacts: list[dict]):
    print(f"\nArtifacts that would be generated ({len(artifacts)}):")
    print(f"{'ID':<25} {'Name':<25} {'Category':<15} {'Priority'}")
    print("-" * 75)
    for a in artifacts:
        print(f"{a['id']:<25} {a['name']:<25} {a['category']:<15} {a['priority']}")


def _print_validation_result(result):
    from opencode_arch.cli.docs_validator import DocsValidationResult
    status = "PASS" if result.is_valid else "FAIL"
    print(f"\nDocs Validation: {status}")
    print(f"  Artifacts: {result.total_artifacts} ({result.passed} passed, {result.failed} failed)")
    if result.issues:
        print(f"  Issues:    {len(result.issues)}")
        for issue in result.issues[:20]:  # cap display
            sev = "ERR" if issue.severity == "error" else "WRN"
            print(f"    [{sev}] {issue.artifact_id}:{issue.line} {issue.issue_type}: {issue.message}")
        if len(result.issues) > 20:
            print(f"    ... and {len(result.issues) - 20} more")
    if not result.is_valid:
        sys.exit(1)


def _print_export_result(result: dict):
    if result.get("error"):
        print(f"Export failed: {result['error']}")
        sys.exit(1)
    print(f"\nExport Complete")
    print(f"  Output:  {result['output']}")
    print(f"  Format:  {result['format']}")
    print(f"  Files:   {result['file_count']}")
    print(f"  Size:    {result['total_size_bytes']:,} bytes")
    print(f"  Prefix:  {result['prefix']}")


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


def _print_regen_result(result: dict):
    if result.get("error"):
        print(f"Regen-loop failed: {result['error']}")
        sys.exit(1)

    print(f"\nRegen-Loop Results")
    print("-" * 60)
    print(f"  Subsystems:  {result['total_subsystems']}")
    print(f"  Converged:   {result['converged_subsystems']}/{result['total_subsystems']}")
    print(f"  Time:        {result['time_seconds']:.1f}s")

    sub_results = result.get("subsystem_results", {})
    if sub_results:
        print(f"\n  Per-subsystem:")
        for name, sub in sub_results.items():
            status = "OK" if sub.get("converged") else "INCOMPLETE"
            print(f"    [{status:10}] {name:20} pass_rate={sub.get('pass_rate', 0):.0%} iter={sub.get('iterations', 0)}")

    full = result.get("full_test_result", {})
    if full.get("total", 0) > 0:
        print(f"\n  Full suite:  {full['passed']}/{full['total']} ({full['pass_rate']:.0%})")

    # Show report card if available
    report = result.get("report_card")
    if report:
        print(f"\n  Report Card: Grade {report['grade']}")
        print(f"    Fidelity:    {report['fidelity']:.0%}")
        print(f"    Compression: {report['compression_ratio']:.1f}x")
        if report.get("improvement_actions"):
            print(f"    Actions:")
            for action in report["improvement_actions"]:
                print(f"      - {action}")


if __name__ == "__main__":
    main()
