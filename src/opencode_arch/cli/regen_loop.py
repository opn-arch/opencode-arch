"""Regen-loop orchestrator — iterative subsystem-decomposed code regeneration."""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from architecture_model.core.decomposer import test_affinity_decompose
from architecture_model.manifest.test_analyzer import analyze_test_file

from opencode_arch.cli.gap_analyzer import analyze_gaps
from opencode_arch.prompts.regen import FEEDBACK_HEADER, REGEN_PROMPT
from opencode_arch.runner.base import RunnerBackend


def run_subsystem_tests(test_files: list[Path], repo_path: Path) -> dict[str, Any]:
    """Run pytest on specific test files and return structured results.

    Args:
        test_files: List of test file paths to run.
        repo_path: Root path of the repository (used as cwd).

    Returns:
        {"passed": int, "failed": int, "total": int, "pass_rate": float, "output": str}
    """
    if not test_files:
        return {"passed": 0, "failed": 0, "total": 0, "pass_rate": 0.0, "output": "No test files."}

    # Filter to existing test files only
    existing = [str(f) for f in test_files if f.exists()]
    if not existing:
        return {"passed": 0, "failed": 0, "total": 0, "pass_rate": 0.0, "output": "No test files found."}

    cmd = [sys.executable, "-m", "pytest"] + existing + ["-v", "--tb=short", "-q"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(repo_path),
        )
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return {"passed": 0, "failed": 0, "total": 0, "pass_rate": 0.0,
                "output": "Test execution timed out (120s)."}
    except Exception as e:
        return {"passed": 0, "failed": 0, "total": 0, "pass_rate": 0.0,
                "output": f"Error running tests: {e}"}

    passed, failed, total = _parse_pytest_summary(output)
    pass_rate = passed / total if total > 0 else 0.0

    return {
        "passed": passed,
        "failed": failed,
        "total": total,
        "pass_rate": pass_rate,
        "output": output,
    }


def _parse_pytest_summary(output: str) -> tuple[int, int, int]:
    """Parse pytest output to extract pass/fail counts.

    Handles both:
        - "5 passed, 2 failed" (standard summary)
        - "X passed" or "X failed" standalone
    """
    import re

    passed = 0
    failed = 0

    # Match the short summary line: "= 5 passed, 2 failed in 0.3s ="
    summary_pattern = re.compile(
        r"(\d+)\s+passed"
        r"(?:.*?(\d+)\s+failed)?"
    )
    # Also check for failed-only: "2 failed"
    failed_only = re.compile(r"(\d+)\s+failed")

    for line in reversed(output.splitlines()):
        m = summary_pattern.search(line)
        if m:
            passed = int(m.group(1))
            if m.group(2):
                failed = int(m.group(2))
            # Check if there's a failed count on the same line we missed
            fm = failed_only.search(line)
            if fm:
                failed = int(fm.group(1))
            break
        # Check if line is failed-only (no passed)
        fm = failed_only.search(line)
        if fm and "passed" not in line:
            failed = int(fm.group(1))
            break

    total = passed + failed
    return passed, failed, total


def _build_prompt(
    subsystem_name: str,
    source_files: list[Path],
    model_context: str,
    constants: list,
    signatures: list,
    contracts: list,
    dependency_apis: str,
    iteration: int,
    max_iterations: int,
    previous_feedback: str,
) -> str:
    """Build the regen prompt for a subsystem iteration."""
    # Format source files
    files_str = "\n".join(f"- {f}" for f in source_files) if source_files else "- (none specified)"

    # Format constants
    if constants:
        consts_str = "\n".join(f"- {c.name} = {c.value!r}  ({c.context})" for c in constants)
    else:
        consts_str = "(none extracted)"

    # Format signatures
    if signatures:
        sigs_parts = []
        for sig in signatures:
            params = ", ".join(sig.params) if sig.params else ""
            ret = f" -> {sig.returns}" if sig.returns else ""
            sigs_parts.append(f"- {sig.name}({params}){ret}")
        sigs_str = "\n".join(sigs_parts)
    else:
        sigs_str = "(none extracted)"

    # Format contracts
    if contracts:
        contract_parts = []
        for c in contracts:
            contract_parts.append(f"- [{c.contract_type}] {c.assertion} (from {c.test_method})")
        contracts_str = "\n".join(contract_parts[:50])  # Cap at 50 to manage token budget
        if len(contracts) > 50:
            contracts_str += f"\n  ... and {len(contracts) - 50} more"
    else:
        contracts_str = "(none extracted)"

    # Format feedback section
    if previous_feedback:
        feedback_str = FEEDBACK_HEADER.format(
            prev_iteration=iteration - 1,
            failure_analysis=previous_feedback,
        )
    else:
        feedback_str = ""

    return REGEN_PROMPT.format(
        subsystem_name=subsystem_name,
        iteration=iteration,
        max_iterations=max_iterations,
        source_files=files_str,
        model_context=model_context or "(no architecture model available)",
        constants=consts_str,
        signatures=sigs_str,
        test_contracts=contracts_str,
        dependency_apis=dependency_apis or "(no dependency context)",
        previous_feedback=feedback_str,
    )


async def run_regen_loop(
    repo_path: Path,
    runner: RunnerBackend,
    max_iterations: int = 5,
    target_pass_rate: float = 0.5,
    subsystem_name: str | None = None,
) -> dict[str, Any]:
    """Run the test-as-oracle decomposed regen loop.

    Decomposes the repo into subsystems by test affinity, then iteratively
    regenerates code per subsystem using the LLM, running tests after each
    attempt to measure convergence.

    Args:
        repo_path: Path to the target repository.
        runner: RunnerBackend for LLM invocation.
        max_iterations: Max iterations per subsystem (default 5).
        target_pass_rate: Stop when this pass rate is achieved (default 0.5).
        subsystem_name: If set, only process this subsystem.

    Returns:
        Summary dict with per-subsystem results and overall metrics.
    """
    start_time = time.time()
    repo_path = Path(repo_path).resolve()

    if not repo_path.exists():
        return {"error": f"Path does not exist: {repo_path}", "success": False}

    # Step 1: Decompose into subsystems
    subsystems = test_affinity_decompose(repo_path)
    if not subsystems:
        return {"error": "No subsystems found (no test files?)", "success": False}

    # Step 2: Filter if specific subsystem requested
    if subsystem_name:
        subsystems = [s for s in subsystems if s.name == subsystem_name]
        if not subsystems:
            return {"error": f"Subsystem '{subsystem_name}' not found", "success": False}

    # Step 3: Try to load architecture model context
    model_context = _load_model_context(repo_path)

    # Step 4: Process each subsystem
    results: dict[str, dict[str, Any]] = {}

    for subsystem in subsystems:
        sub_result = await _process_subsystem(
            subsystem=subsystem,
            repo_path=repo_path,
            runner=runner,
            model_context=model_context,
            max_iterations=max_iterations,
            target_pass_rate=target_pass_rate,
        )
        results[subsystem.name] = sub_result

        # Record in telemetry
        _record_outcome(
            repo_path=repo_path,
            subsystem=subsystem,
            result=sub_result,
        )

    # Step 5: Run full test suite as integration check
    all_test_files = []
    for s in subsystems:
        all_test_files.extend(s.test_files)
    full_result = run_subsystem_tests(all_test_files, repo_path) if all_test_files else {}

    elapsed = time.time() - start_time

    # Summary
    converged = sum(1 for r in results.values() if r.get("converged", False))
    total_subs = len(results)

    return {
        "success": True,
        "subsystem_results": results,
        "total_subsystems": total_subs,
        "converged_subsystems": converged,
        "full_test_result": full_result,
        "time_seconds": elapsed,
    }


async def _process_subsystem(
    subsystem,
    repo_path: Path,
    runner: RunnerBackend,
    model_context: str,
    max_iterations: int,
    target_pass_rate: float,
) -> dict[str, Any]:
    """Process a single subsystem through the regen loop."""
    # Analyze test files for contracts and constants
    all_contracts = []
    all_constants = []
    all_imports = []

    for test_file in subsystem.test_files:
        if test_file.exists():
            try:
                analysis = analyze_test_file(test_file)
                all_contracts.extend(analysis.contracts)
                all_constants.extend(analysis.constants)
                all_imports.extend(analysis.required_imports)
            except Exception:
                pass  # Gracefully skip unparseable test files

    # Build dependency context (APIs from subsystems we depend on)
    dependency_apis = _build_dependency_context(subsystem, repo_path)

    # Iterative loop
    best_pass_rate = 0.0
    feedback = ""
    iterations_used = 0

    for iteration in range(1, max_iterations + 1):
        iterations_used = iteration

        # Build prompt
        prompt = _build_prompt(
            subsystem_name=subsystem.name,
            source_files=subsystem.source_files,
            model_context=model_context,
            constants=all_constants,
            signatures=[],  # Filled when model has enriched components
            contracts=all_contracts,
            dependency_apis=dependency_apis,
            iteration=iteration,
            max_iterations=max_iterations,
            previous_feedback=feedback,
        )

        # Call LLM via runner
        run_result = await runner.run(prompt=prompt, repo_path=str(repo_path))

        # Run subsystem tests
        test_result = run_subsystem_tests(subsystem.test_files, repo_path)
        pass_rate = test_result["pass_rate"]

        if pass_rate > best_pass_rate:
            best_pass_rate = pass_rate

        # Check convergence
        if pass_rate >= target_pass_rate:
            return {
                "converged": True,
                "pass_rate": pass_rate,
                "iterations": iteration,
                "tests_passed": test_result["passed"],
                "tests_total": test_result["total"],
            }

        # Analyze gaps for next iteration
        feedback = analyze_gaps(test_result["output"], model_context)

    # Did not converge
    return {
        "converged": False,
        "pass_rate": best_pass_rate,
        "iterations": iterations_used,
        "tests_passed": 0,
        "tests_total": 0,
        "last_feedback": feedback,
    }


def _load_model_context(repo_path: Path) -> str:
    """Try to load architecture model context for the repo."""
    model_file = repo_path / ".architecture-model.yaml"
    if not model_file.exists():
        return ""

    try:
        from architecture_model.core.parser import load_model
        from architecture_model.integrations.llm_context import format_model_context

        model = load_model(model_file)
        return format_model_context(model, max_tokens=2000, detail_level="standard")
    except Exception:
        return ""


def _build_dependency_context(subsystem, repo_path: Path) -> str:
    """Build context string for dependency APIs (public interfaces of upstream subsystems)."""
    if not subsystem.dependencies:
        return ""

    parts = []
    for dep_name in subsystem.dependencies:
        parts.append(f"- Depends on subsystem '{dep_name}'")
    return "\n".join(parts)


def _record_outcome(repo_path: Path, subsystem, result: dict[str, Any]):
    """Record regen outcome to telemetry store."""
    try:
        from opencode_arch.telemetry.store import TelemetryStore
        store = TelemetryStore()
        store.log_regen_outcome(
            repo=repo_path.name,
            subsystem=subsystem.name,
            iteration=result.get("iterations", 0),
            features={
                "constant_count": 0,
                "signature_count": 0,
                "contract_count": 0,
            },
            pass_rate=result.get("pass_rate", 0.0),
            time_seconds=0.0,
        )
    except Exception:
        pass  # Telemetry is best-effort
