# src/opencode_arch/mcp/tools/generate.py
"""architect_generate MCP tool — run tests on generated code."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from opencode_arch.mcp.quality import with_quality


@with_quality
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
        parsed = _parse_pytest_output(output, result.returncode)

        try:
            from opencode_arch.telemetry.collector import drain_and_store

            drain_and_store(tool="architect_generate", repo=path.name)
        except Exception:
            pass

        return parsed

    except subprocess.TimeoutExpired:
        return {
            "error": "Test execution timed out (120s)",
            "passed": False,
            "pass_rate": 0.0,
            "total_tests": 0,
        }
    except Exception as e:
        return {
            "error": f"Test execution failed: {e}",
            "passed": False,
            "pass_rate": 0.0,
            "total_tests": 0,
        }


def _parse_pytest_output(output: str, returncode: int) -> dict[str, Any]:
    """Parse pytest output to extract pass/fail counts."""
    import re

    total = 0
    passed_count = 0
    failed_count = 0
    failures: list[str] = []

    # Match the pytest summary line: "=== N passed, M failed, K errors in Xs ==="
    # or "N passed in Xs" or "N failed in Xs"
    summary_pattern = re.compile(
        r"=+\s*(.*?)\s*=+\s*$|^(\d+\s+(?:passed|failed|error).*in\s+[\d.]+s)\s*$",
        re.MULTILINE,
    )
    count_pattern = re.compile(
        r"(\d+)\s+(passed|failed|error|errors|warnings?|deselected|skipped|xfailed|xpassed)"
    )

    for match in summary_pattern.finditer(output):
        summary_text = match.group(1) or match.group(2) or ""
        for count_match in count_pattern.finditer(summary_text):
            count = int(count_match.group(1))
            category = count_match.group(2)
            if category == "passed":
                passed_count = count
            elif category == "failed":
                failed_count = count
            elif category in ("error", "errors"):
                failed_count += count

    total = passed_count + failed_count

    # Capture FAILED test names
    for line in output.split("\n"):
        if line.startswith("FAILED"):
            failures.append(line.strip())

    if total == 0 and "no tests ran" in output.lower():
        return {
            "passed": True,
            "pass_rate": 0.0,
            "total_tests": 0,
            "passed_tests": 0,
            "failures": [],
        }

    pass_rate = passed_count / total if total > 0 else 0.0

    return {
        "passed": returncode == 0,
        "pass_rate": pass_rate,
        "total_tests": total,
        "passed_tests": passed_count,
        "failures": failures,
    }
