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
