"""OpenCode subprocess runner backend."""
from __future__ import annotations

import subprocess

from opencode_arch.runner.base import RunResult


class OpencodeRunner:
    """Invokes `opencode run` as a subprocess."""

    def __init__(self, timeout: int = 600, model: str | None = None):
        self.timeout = timeout
        self.model = model

    async def run(self, prompt: str, repo_path: str) -> RunResult:
        """Run OpenCode with a prompt in the given repo directory.

        Uses stdin to pass the prompt (avoids ARG_MAX limits for long prompts).
        Uses cwd to set the working directory (no --dir flag needed).
        """
        cmd = ["opencode", "run"]
        if self.model:
            cmd.extend(["--model", self.model])

        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=repo_path,
            )
            # Strip ANSI escape codes from output
            output = _strip_ansi(result.stdout)
            return RunResult(
                output=output,
                exit_code=result.returncode,
                success=result.returncode == 0,
            )
        except subprocess.TimeoutExpired:
            return RunResult(
                output=f"Timeout: opencode run exceeded {self.timeout}s",
                exit_code=-1,
                success=False,
            )
        except FileNotFoundError:
            return RunResult(
                output="Error: opencode not found. Install with: npm i -g opencode",
                exit_code=-1,
                success=False,
            )
        except Exception as e:
            return RunResult(
                output=f"Error: {e}",
                exit_code=-1,
                success=False,
            )


    def run_via_policy(
        self,
        prompt: str,
        *,
        task_class_name: str,
        repo_path: str = ".",
    ) -> RunResult:
        """Route through Policy.pick(...).complete(...) if policy configured, else fall back to run().

        Synchronous. Wraps Completion into RunResult for caller compatibility.
        Falls back to asyncio.run(self.run(prompt, repo_path)) if no policy.yaml found.
        """
        from pathlib import Path as _P
        policy_path = _P(repo_path) / ".architecture" / "llm" / "policy.yaml"
        if not policy_path.exists():
            import asyncio
            return asyncio.run(self.run(prompt, repo_path))
        from opencode_arch.llm.policy import load_policy, TaskClass
        policy = load_policy(_P(repo_path))
        provider = policy.pick(TaskClass(task_class_name))
        completion = provider.complete(prompt, model=self.model, max_tokens=4096)
        return RunResult(
            output=completion["text"],
            exit_code=0,
            success=True,
        )


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    import re
    ansi_pattern = re.compile(r'\x1b\[[0-9;]*m|\x1b\[\?[0-9;]*[a-zA-Z]|\x1b\[[0-9;]*[a-zA-Z]')
    return ansi_pattern.sub('', text)
