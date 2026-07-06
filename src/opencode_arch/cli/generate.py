"""Generate command - test-guided code generation loop."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from opencode_arch.runner.base import RunnerBackend
from opencode_arch.cli.prompts import GENERATE_PROMPT


async def run_generate(
    repo_path: str,
    runner: RunnerBackend,
    max_iter: int = 3,
    test_command: str | None = None,
) -> dict[str, Any]:
    """Run the test-guided code generation loop."""
    path = Path(repo_path)
    if not path.exists():
        return {"error": f"Path does not exist: {repo_path}", "passed": False}

    start_time = time.time()
    iterations = 0
    last_test_result = {}

    from opencode_arch.mcp.tools.generate import run_tests_on_generated_code

    for i in range(max_iter):
        iterations = i + 1

        prompt = GENERATE_PROMPT.format(repo_path=str(path.resolve()), max_iter=max_iter)
        if i > 0 and last_test_result.get("failures"):
            failures_str = "\n".join(last_test_result["failures"][:10])
            prompt += f"\n\nPrevious failures (iteration {i}):\n{failures_str}\nFix these issues."

        await runner.run(prompt=prompt, repo_path=str(path))

        test_result = await run_tests_on_generated_code(repo_path=str(path), test_command=test_command)
        last_test_result = test_result

        if test_result.get("passed") or test_result.get("pass_rate", 0) == 1.0:
            break
        if test_result.get("total_tests", 0) == 0:
            break

    elapsed = time.time() - start_time

    try:
        from opencode_arch.telemetry.store import TelemetryStore
        store = TelemetryStore()
        store.record(
            tool="architect_generate", repo=path.name,
            context_tokens=0, output_quality=int(last_test_result.get("pass_rate", 0) * 100),
            iterations=iterations,
        )
    except Exception:
        pass

    return {
        "passed": last_test_result.get("passed", False),
        "pass_rate": last_test_result.get("pass_rate", 0.0),
        "total_tests": last_test_result.get("total_tests", 0),
        "passed_tests": last_test_result.get("passed_tests", 0),
        "failures": last_test_result.get("failures", []),
        "iterations": iterations,
        "time_seconds": elapsed,
    }
