"""Regen-loop orchestrator — iterative subsystem-decomposed code regeneration."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from architecture_model.core.decomposer import test_affinity_decompose
from architecture_model.manifest.test_analyzer import analyze_test_file

from opencode_arch.cli.gap_analyzer import analyze_gaps
from opencode_arch.prompts.regen import FEEDBACK_HEADER, REGEN_PROMPT
from opencode_arch.runner.base import RunnerBackend


@dataclass
class PromptMetrics:
    """Token metrics for each prompt section."""

    total_tokens: int
    model_context_tokens: int
    signatures_tokens: int
    constants_tokens: int
    contracts_tokens: int
    dependency_tokens: int
    feedback_tokens: int
    source_equivalent_tokens: int  # what agent would read without extension
    compression_ratio: float  # source_equivalent / total


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

    cmd = [sys.executable, "-m", "pytest"] + existing + [
        "-v", "--tb=short", "-q",
        "-W", "ignore::pytest.PytestConfigWarning",
        "--override-ini=timeout=0",
    ]

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


def _setup_blind_workdir(repo_path: Path, test_files: list[Path]) -> Path:
    """Create a temporary working directory for blind mode.

    Copies only test infrastructure (test files, __init__.py for package
    structure, conftest.py, pyproject.toml/setup.py) into a temp dir.
    The agent cannot see original source files — all behavioral info
    must come from the prompt.

    Args:
        repo_path: Original repository root.
        test_files: Test files to copy into the blind workdir.

    Returns:
        Path to the temporary working directory.
    """
    work_dir = Path(tempfile.mkdtemp(prefix="blind-regen-"))
    repo_path = repo_path.resolve()

    # Copy test files, preserving relative path structure
    for test_file in test_files:
        if not test_file.exists():
            continue
        test_file = test_file.resolve()
        rel = test_file.relative_to(repo_path)
        dest = work_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(test_file, dest)

    # Create __init__.py files for all parent packages to maintain import structure
    for test_file in test_files:
        if not test_file.exists():
            continue
        test_file = test_file.resolve()
        rel = test_file.relative_to(repo_path)
        # Walk up from test file's parent to repo root, creating __init__.py
        current = rel.parent
        while current != Path("."):
            init_src = repo_path / current / "__init__.py"
            init_dest = work_dir / current / "__init__.py"
            if not init_dest.exists():
                init_dest.parent.mkdir(parents=True, exist_ok=True)
                if init_src.exists():
                    shutil.copy2(init_src, init_dest)
                else:
                    init_dest.write_text("")
            current = current.parent

    # Copy conftest.py files from directories containing test files
    copied_conftest_dirs: set[Path] = set()
    for test_file in test_files:
        if not test_file.exists():
            continue
        test_file = test_file.resolve()
        rel = test_file.relative_to(repo_path)
        # Check test file's directory and all parents for conftest.py
        current = rel.parent
        while True:
            if current not in copied_conftest_dirs:
                conftest_src = repo_path / current / "conftest.py"
                if conftest_src.exists():
                    conftest_dest = work_dir / current / "conftest.py"
                    conftest_dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(conftest_src, conftest_dest)
                copied_conftest_dirs.add(current)
            if current == Path("."):
                break
            current = current.parent

    # Also check root-level conftest.py
    root_conftest = repo_path / "conftest.py"
    if root_conftest.exists() and Path(".") not in copied_conftest_dirs:
        shutil.copy2(root_conftest, work_dir / "conftest.py")

    # Copy test helper modules (non-test .py files) from test directories.
    # These are shared utilities that test files import (e.g., tests/helpers.py).
    # A file is a "test file" if: test_*.py, tests_*.py, or *_test.py
    def _is_test_file(name: str) -> bool:
        return (
            name.startswith("test_")
            or name.startswith("tests_")
            or name.endswith("_test.py")
        ) and name.endswith(".py")

    def _find_test_root(test_file: Path) -> Path | None:
        """Find the closest ancestor directory named 'tests' or 'test'."""
        rel = test_file.relative_to(repo_path)
        # Walk up the path to find a directory named tests/test
        for i, part in enumerate(rel.parts):
            if part in ("tests", "test"):
                return repo_path / Path(*rel.parts[: i + 1])
        # Fallback: use the direct parent of the test file
        return test_file.parent

    # Find test root directories from the test file paths
    resolved_test_files = {tf.resolve() for tf in test_files if tf.exists()}
    test_roots: set[Path] = set()
    for tf in resolved_test_files:
        root = _find_test_root(tf)
        if root and root.is_dir():
            test_roots.add(root)

    # Walk each test root and copy infrastructure files (helpers, __init__.py, conftest.py)
    for test_root in test_roots:
        for py_file in test_root.rglob("*.py"):
            if not py_file.is_file():
                continue
            # Skip test files that aren't in our subsystem
            if _is_test_file(py_file.name) and py_file.resolve() not in resolved_test_files:
                continue
            # Copy infrastructure files (conftest, __init__, helpers) if not already present
            rel = py_file.relative_to(repo_path)
            dest = work_dir / rel
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(py_file, dest)

    # Copy pyproject.toml / setup.py / pytest config for import resolution
    for config_file in ("pyproject.toml", "setup.py", "setup.cfg", "pytest.ini", "tox.ini"):
        src = repo_path / config_file
        if src.exists():
            shutil.copy2(src, work_dir / config_file)

    return work_dir


def _extract_signatures_for_subsystem(repo_path: Path, subsystem) -> list:
    """Extract FunctionSignature data from the architecture model for a subsystem.

    Loads the .architecture-model.yaml and finds signatures associated with
    the subsystem's components. Returns signature objects with body_hint included.

    Args:
        repo_path: Path to the repository (where .architecture-model.yaml lives).
        subsystem: Subsystem with source_files to match against components.

    Returns:
        List of signature-like objects with name, params, returns, body_hint.
    """
    model_file = repo_path / ".architecture-model.yaml"
    if not model_file.exists():
        return []

    try:
        from architecture_model.core.parser import load_model

        model = load_model(model_file)
        signatures = []

        # Get source file stems for matching
        source_stems = {f.stem for f in subsystem.source_files}

        for comp in model.entities.components:
            # Match component to subsystem by checking if its source files overlap
            comp_files = getattr(comp, "files", [])
            comp_stems = {Path(f).stem for f in comp_files} if comp_files else set()

            # Also match by component name (stem of source file)
            if comp_stems:
                if not source_stems.intersection(comp_stems):
                    continue
            elif comp.name not in source_stems:
                continue

            # Extract signatures from component
            for sig in getattr(comp, "signatures", []):
                signatures.append(sig)

        return signatures
    except Exception:
        return []


def _extract_constants_for_subsystem(repo_path: Path, subsystem) -> list:
    """Extract Constant objects from the architecture model for a subsystem.

    Returns constants from matched components (module constants, class attributes,
    module-level instances) that may not appear in test-derived constants.
    """
    model_file = repo_path / ".architecture-model.yaml"
    if not model_file.exists():
        return []

    try:
        from architecture_model.core.parser import load_model

        model = load_model(model_file)
        constants = []

        source_stems = {f.stem for f in subsystem.source_files}

        for comp in model.entities.components:
            comp_files = getattr(comp, "files", [])
            comp_stems = {Path(f).stem for f in comp_files} if comp_files else set()

            if comp_stems:
                if not source_stems.intersection(comp_stems):
                    continue
            elif comp.name not in source_stems:
                continue

            for const in getattr(comp, "constants", []):
                constants.append(const)

        return constants
    except Exception:
        return []


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
    source_equivalent_tokens: int = 0,
    contract_cap: int = 50,
) -> tuple[str, PromptMetrics]:
    """Build the regen prompt for a subsystem iteration.

    Returns:
        Tuple of (prompt_string, PromptMetrics with per-section token counts).
    """
    # Format source files
    files_str = "\n".join(f"- {f}" for f in source_files) if source_files else "- (none specified)"

    # Format constants
    if constants:
        consts_str = "\n".join(f"- {c.name} = {c.value!r}  ({c.context})" for c in constants)
    else:
        consts_str = "(none extracted)"

    # Format signatures (include body_hint for blind regen)
    if signatures:
        sigs_parts = []
        for sig in signatures:
            params = ", ".join(sig.params) if sig.params else ""
            ret = f" -> {sig.returns}" if sig.returns else ""
            hint = getattr(sig, "body_hint", "")
            if hint:
                sigs_parts.append(f"- {sig.name}({params}){ret}  [body: {hint}]")
            else:
                sigs_parts.append(f"- {sig.name}({params}){ret}")
        sigs_str = "\n".join(sigs_parts)
    else:
        sigs_str = "(none extracted)"

    # Format contracts
    if contracts:
        contract_parts = []
        for c in contracts:
            contract_parts.append(f"- [{c.contract_type}] {c.assertion} (from {c.test_method})")
        contracts_str = "\n".join(contract_parts[:contract_cap])
        if len(contracts) > contract_cap:
            contracts_str += f"\n  ... and {len(contracts) - contract_cap} more"
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

    # Compute per-section token counts (chars / 4 approximation)
    model_context_str = model_context or "(no architecture model available)"
    dependency_str = dependency_apis or "(no dependency context)"

    model_context_tokens = len(model_context_str) // 4
    signatures_tokens = len(sigs_str) // 4
    constants_tokens = len(consts_str) // 4
    contracts_tokens = len(contracts_str) // 4
    dependency_tokens = len(dependency_str) // 4
    feedback_tokens = len(feedback_str) // 4

    prompt_str = REGEN_PROMPT.format(
        subsystem_name=subsystem_name,
        iteration=iteration,
        max_iterations=max_iterations,
        source_files=files_str,
        model_context=model_context_str,
        constants=consts_str,
        signatures=sigs_str,
        test_contracts=contracts_str,
        dependency_apis=dependency_str,
        previous_feedback=feedback_str,
    )

    total_tokens = len(prompt_str) // 4
    compression_ratio = (
        source_equivalent_tokens / total_tokens if total_tokens > 0 else 0.0
    )

    metrics = PromptMetrics(
        total_tokens=total_tokens,
        model_context_tokens=model_context_tokens,
        signatures_tokens=signatures_tokens,
        constants_tokens=constants_tokens,
        contracts_tokens=contracts_tokens,
        dependency_tokens=dependency_tokens,
        feedback_tokens=feedback_tokens,
        source_equivalent_tokens=source_equivalent_tokens,
        compression_ratio=compression_ratio,
    )

    return prompt_str, metrics


def _compute_source_equivalent(subsystem, repo_path: Path, all_subsystems: list) -> int:
    """Compute tokens needed to read source + deps (the 'without extension' baseline).

    This represents what the agent would need to read WITHOUT the architecture
    model extension — the raw source files of the subsystem plus all its
    dependencies.

    Args:
        subsystem: Subsystem object with .source_files and .dependencies.
        repo_path: Root path of the repository.
        all_subsystems: All subsystems (to resolve dependency source files).

    Returns:
        Estimated token count (chars / 4).
    """
    total_chars = 0
    # Own source files
    for f in subsystem.source_files:
        path = repo_path / f if not Path(f).is_absolute() else Path(f)
        try:
            total_chars += len(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            pass
    # Dependency source files
    for dep_name in subsystem.dependencies:
        for s in all_subsystems:
            if s.name == dep_name:
                for sf in s.source_files:
                    path = repo_path / sf if not Path(sf).is_absolute() else Path(sf)
                    try:
                        total_chars += len(path.read_text(encoding="utf-8"))
                    except (OSError, UnicodeDecodeError):
                        pass
    return total_chars // 4


async def run_regen_loop(
    repo_path: Path,
    runner: RunnerBackend,
    max_iterations: int = 5,
    target_pass_rate: float = 0.5,
    subsystem_name: str | None = None,
    blind: bool = False,
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
        blind: If True, agent works in temp dir without source file access.

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
            blind=blind,
            all_subsystems=subsystems,
        )
        results[subsystem.name] = sub_result

        # Record in telemetry
        _record_outcome(
            repo_path=repo_path,
            subsystem=subsystem,
            result=sub_result,
            mode="blind" if blind else "normal",
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

    # Record learning curve entry
    try:
        from opencode_arch.telemetry.store import TelemetryStore
        store = TelemetryStore()

        all_metrics = [r.get("token_metrics", {}) for r in results.values()]
        avg_prompt = sum(m.get("prompt_tokens", 0) for m in all_metrics) / max(len(all_metrics), 1)
        avg_source = sum(m.get("source_equivalent_tokens", 0) for m in all_metrics) / max(len(all_metrics), 1)
        avg_compression = sum(m.get("compression_ratio", 0) for m in all_metrics) / max(len(all_metrics), 1)
        avg_iters = sum(r.get("iterations", 0) for r in results.values()) / max(len(results), 1)
        avg_pass = sum(r.get("pass_rate", 0) for r in results.values()) / max(len(results), 1)

        store.record_learning_curve(
            repo=repo_path.name,
            mode="blind" if blind else "normal",
            total_subsystems=total_subs,
            converged_subsystems=converged,
            avg_pass_rate=avg_pass,
            avg_iterations=avg_iters,
            avg_prompt_tokens=avg_prompt,
            avg_source_equivalent=avg_source,
            avg_compression_ratio=avg_compression,
            total_time_seconds=elapsed,
        )
    except Exception:
        pass  # Telemetry is best-effort

    # --- Learning loop: generate report card ---
    report_card = None
    try:
        from opencode_arch.learning.assessor import generate_report_card
        from opencode_arch.telemetry.store import TelemetryStore
        import json

        store = TelemetryStore()

        # Get previous fidelity/compression for trend detection
        prev_cards = store.get_report_cards(limit=1)
        prev_fidelity = prev_cards[0]["fidelity"] if prev_cards else None
        prev_compression = prev_cards[0]["compression_ratio"] if prev_cards else None

        report_card = generate_report_card(
            repo=repo_path.name,
            mode="blind" if blind else "normal",
            subsystem_results=results,
            previous_fidelity=prev_fidelity,
            previous_compression=prev_compression,
        )

        # Store report card
        store.record_report_card(
            repo=report_card.repo,
            mode=report_card.mode,
            grade=report_card.grade,
            fidelity=report_card.fidelity,
            compression_ratio=report_card.compression_ratio,
            failure_patterns=json.dumps(report_card.failure_patterns),
            novel_patterns=report_card.novel_patterns,
            improvement_actions=json.dumps(report_card.improvement_actions),
        )
    except Exception:
        pass  # Report card generation is best-effort

    # --- Learning loop: extract lessons ---
    try:
        from opencode_arch.learning.lessons import extract_lessons
        from opencode_arch.telemetry.store import TelemetryStore
        import json

        store = TelemetryStore()
        lessons = extract_lessons(
            repo=repo_path.name,
            mode="blind" if blind else "normal",
            subsystem_results=results,
        )
        for lesson in lessons:
            store.record_lesson(
                lesson_id=lesson.lesson_id,
                discovered_repo=lesson.discovered_repo,
                category=lesson.category,
                description=lesson.description,
                evidence=json.dumps(lesson.evidence),
            )
    except Exception:
        pass  # Lesson extraction is best-effort

    # --- Learning loop: detect and fix documentation drift ---
    try:
        from opencode_arch.learning.maintainer import detect_drift, auto_fix_drift
        from opencode_arch.telemetry.store import TelemetryStore

        store = TelemetryStore()
        drift_flags = detect_drift(repo_path)
        if drift_flags:
            # Record flags
            for flag in drift_flags:
                store.record_drift_flag(
                    file=flag.file,
                    issue=flag.issue,
                    severity=flag.severity,
                    auto_fixable=flag.auto_fixable,
                    suggested_fix=flag.suggested_fix,
                )
            # Attempt auto-fix
            auto_fix_drift(drift_flags, repo_path)
    except Exception:
        pass  # Drift detection is best-effort

    return {
        "success": True,
        "subsystem_results": results,
        "total_subsystems": total_subs,
        "converged_subsystems": converged,
        "full_test_result": full_result,
        "time_seconds": elapsed,
        "report_card": {
            "grade": report_card.grade,
            "fidelity": report_card.fidelity,
            "compression_ratio": report_card.compression_ratio,
            "improvement_actions": report_card.improvement_actions,
        } if report_card else None,
    }


async def _process_subsystem(
    subsystem,
    repo_path: Path,
    runner: RunnerBackend,
    model_context: str,
    max_iterations: int,
    target_pass_rate: float,
    blind: bool = False,
    all_subsystems: list | None = None,
) -> dict[str, Any]:
    """Process a single subsystem through the regen loop."""
    start_time = time.time()

    # In blind mode, set up isolated working directory
    work_dir: Path | None = None
    if blind:
        work_dir = _setup_blind_workdir(repo_path, subsystem.test_files)

    # Determine effective paths for runner and tests
    effective_path = work_dir if blind else repo_path

    # In blind mode, remap test file paths to the work_dir
    if blind and work_dir:
        effective_test_files = []
        for tf in subsystem.test_files:
            if tf.exists():
                rel = tf.resolve().relative_to(repo_path)
                effective_test_files.append(work_dir / rel)
            else:
                effective_test_files.append(tf)
    else:
        effective_test_files = subsystem.test_files

    # In blind mode, extract signatures from architecture model
    signatures = []
    model_constants = []
    if blind:
        signatures = _extract_signatures_for_subsystem(repo_path, subsystem)
        model_constants = _extract_constants_for_subsystem(repo_path, subsystem)

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

    # In blind mode, merge model constants (module-level, class attrs, instances)
    # with test-derived constants, deduplicating by name
    if blind and model_constants:
        existing_names = {c.name for c in all_constants}
        for mc in model_constants:
            if mc.name not in existing_names:
                all_constants.append(mc)
                existing_names.add(mc.name)

    # Build dependency context (APIs from subsystems we depend on)
    dependency_apis = _build_dependency_context(subsystem, repo_path)

    # Compute source-equivalent token baseline
    source_equivalent_tokens = _compute_source_equivalent(
        subsystem, repo_path, all_subsystems or []
    )

    # --- Learning loop: proactive adaptations ---
    contract_cap = 50
    try:
        from opencode_arch.learning.adapter import get_adaptations, apply_adaptations

        # Compute body_hint coverage for this subsystem
        sigs_with_hints = sum(1 for s in signatures if getattr(s, "body_hint", ""))
        body_hint_coverage = sigs_with_hints / len(signatures) if signatures else 0.0

        adaptations = get_adaptations(
            subsystem_name=subsystem.name,
            dependency_count=len(subsystem.dependencies),
            signature_count=len(signatures),
            contract_count=len(all_contracts),
            body_hint_coverage=body_hint_coverage,
        )
        if adaptations:
            adapted = apply_adaptations(adaptations, contract_cap=50)
            contract_cap = adapted.get("contract_cap", 50)
    except Exception:
        pass  # Learning adaptations are best-effort

    # Iterative loop
    best_pass_rate = 0.0
    feedback = ""
    iterations_used = 0
    last_metrics: PromptMetrics | None = None
    all_failure_patterns: dict[str, int] = {}

    for iteration in range(1, max_iterations + 1):
        iterations_used = iteration

        # Build prompt — in blind mode, show relative paths for file creation
        if blind:
            display_files = [f.resolve().relative_to(repo_path) for f in subsystem.source_files if f.exists()]
        else:
            display_files = subsystem.source_files

        prompt, metrics = _build_prompt(
            subsystem_name=subsystem.name,
            source_files=display_files,
            model_context=model_context,
            constants=all_constants,
            signatures=signatures,
            contracts=all_contracts,
            dependency_apis=dependency_apis,
            iteration=iteration,
            max_iterations=max_iterations,
            previous_feedback=feedback,
            source_equivalent_tokens=source_equivalent_tokens,
            contract_cap=contract_cap,
        )
        last_metrics = metrics

        # Call LLM via runner
        run_result = await runner.run(prompt=prompt, repo_path=str(effective_path))

        # Run subsystem tests
        test_result = run_subsystem_tests(effective_test_files, effective_path)
        pass_rate = test_result["pass_rate"]

        if pass_rate > best_pass_rate:
            best_pass_rate = pass_rate

        # Check convergence
        if pass_rate >= target_pass_rate:
            token_metrics = _format_token_metrics(metrics)
            return {
                "converged": True,
                "pass_rate": pass_rate,
                "iterations": iteration,
                "tests_passed": test_result["passed"],
                "tests_total": test_result["total"],
                "features": {
                    "constant_count": len(all_constants),
                    "signature_count": len(signatures),
                    "contract_count": len(all_contracts),
                },
                "token_metrics": token_metrics,
                "failure_patterns": all_failure_patterns,
                "time_seconds": time.time() - start_time,
            }

        # --- Learning loop: classify failures ---
        try:
            from opencode_arch.learning.classifier import classify_failures
            classifications = classify_failures(
                test_output=test_result["output"],
                pass_rate=pass_rate,
                total_tests=test_result["total"],
                failed_tests=test_result["failed"],
            )
            for c in classifications:
                pattern_name = c.pattern.value
                all_failure_patterns[pattern_name] = all_failure_patterns.get(pattern_name, 0) + 1
        except Exception:
            pass  # Classification is best-effort

        # Analyze gaps for next iteration
        feedback = analyze_gaps(test_result["output"], model_context)

    # Did not converge
    token_metrics = _format_token_metrics(last_metrics) if last_metrics else {}
    return {
        "converged": False,
        "pass_rate": best_pass_rate,
        "iterations": iterations_used,
        "tests_passed": 0,
        "tests_total": 0,
        "last_feedback": feedback,
        "features": {
            "constant_count": len(all_constants),
            "signature_count": len(signatures),
            "contract_count": len(all_contracts),
        },
        "token_metrics": token_metrics,
        "failure_patterns": all_failure_patterns,
        "time_seconds": time.time() - start_time,
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
    """Build rich context string for dependency APIs.

    Loads the architecture model and extracts the public API surface
    (constants, classes, function signatures) of each dependency subsystem's
    components. This gives the blind regen agent enough information to produce
    correct imports and usage without access to source files.

    Args:
        subsystem: Subsystem object with .dependencies list of dep names.
        repo_path: Path to repo root (where .architecture-model.yaml lives).

    Returns:
        Formatted string with API surface per dependency, or "" if no deps.
    """
    if not subsystem.dependencies:
        return ""

    model_file = repo_path / ".architecture-model.yaml"
    if not model_file.exists():
        # Fallback: just list dependency names
        parts = []
        for dep_name in subsystem.dependencies:
            parts.append(f"- Depends on subsystem '{dep_name}'")
        return "\n".join(parts)

    try:
        from architecture_model.core.parser import load_model

        model = load_model(model_file)
    except Exception:
        # Model failed to load — fallback to names only
        parts = []
        for dep_name in subsystem.dependencies:
            parts.append(f"- Depends on subsystem '{dep_name}'")
        return "\n".join(parts)

    # Build a mapping from dependency name -> matched components
    sections = []

    for dep_name in subsystem.dependencies:
        # Find components that match this dependency (by component name or file stem)
        matched_components = []
        for comp in model.entities.components:
            comp_files = getattr(comp, "files", [])
            comp_stems = {Path(f).stem for f in comp_files} if comp_files else set()

            if dep_name in comp_stems or comp.name == dep_name:
                matched_components.append(comp)

        if not matched_components:
            sections.append(f"#### Module: {dep_name}\n  (no model data available)")
            continue

        for comp in matched_components:
            lines = [f"#### Module: {dep_name}"]

            # Constants
            for const in getattr(comp, "constants", []) or []:
                const_type = getattr(const, "type", None) or ""
                const_value = getattr(const, "value", None) or ""
                if const_type and const_value:
                    lines.append(f"  {const.name}: {const_type} = {const_value}")
                elif const_value:
                    lines.append(f"  {const.name} = {const_value}")
                else:
                    lines.append(f"  {const.name}")

            # Class symbols
            for sym in getattr(comp, "symbols", []) or []:
                kind = getattr(sym, "kind", "")
                if kind == "class":
                    supers = getattr(sym, "supers", []) or []
                    supers_str = ", ".join(supers) if supers else ""
                    if supers_str:
                        lines.append(f"  class {sym.name}({supers_str}):")
                    else:
                        lines.append(f"  class {sym.name}:")
                    members = getattr(sym, "members", []) or []
                    for member in members:
                        lines.append(f"    .{member}")

            # Function signatures (NO body_hint for deps — that's only for current subsystem)
            for sig in getattr(comp, "signatures", []) or []:
                params = ", ".join(sig.params) if sig.params else ""
                ret = f" -> {sig.returns}" if getattr(sig, "returns", None) else ""
                lines.append(f"  def {sig.name}({params}){ret}")

            sections.append("\n".join(lines))

    return "\n\n".join(sections)


def _format_token_metrics(metrics: PromptMetrics) -> dict[str, Any]:
    """Format PromptMetrics into a serializable dict for result tracking."""
    return {
        "prompt_tokens": metrics.total_tokens,
        "source_equivalent_tokens": metrics.source_equivalent_tokens,
        "compression_ratio": metrics.compression_ratio,
        "sections": {
            "model_context": metrics.model_context_tokens,
            "signatures": metrics.signatures_tokens,
            "constants": metrics.constants_tokens,
            "contracts": metrics.contracts_tokens,
            "dependency_apis": metrics.dependency_tokens,
            "feedback": metrics.feedback_tokens,
        },
    }


def _record_outcome(repo_path: Path, subsystem, result: dict[str, Any], mode: str = "normal"):
    """Record regen outcome to telemetry store."""
    try:
        from opencode_arch.telemetry.store import TelemetryStore
        store = TelemetryStore()
        features = result.get("features", {})
        token_metrics = result.get("token_metrics", {})
        store.log_regen_outcome(
            repo=repo_path.name,
            subsystem=subsystem.name,
            iteration=result.get("iterations", 0),
            features={
                "constant_count": features.get("constant_count", 0),
                "signature_count": features.get("signature_count", 0),
                "contract_count": features.get("contract_count", 0),
            },
            pass_rate=result.get("pass_rate", 0.0),
            time_seconds=result.get("time_seconds", 0.0),
            prompt_tokens=token_metrics.get("prompt_tokens", 0),
            source_equivalent_tokens=token_metrics.get("source_equivalent_tokens", 0),
            compression_ratio=token_metrics.get("compression_ratio", 0.0),
            mode=mode,
        )
    except Exception:
        pass  # Telemetry is best-effort
