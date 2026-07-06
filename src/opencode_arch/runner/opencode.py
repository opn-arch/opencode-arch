"""OpenCode subprocess runner backend."""
from __future__ import annotations

import subprocess

from opencode_arch.runner.base import RunResult


class OpencodeRunner:
    """Invokes `opencode run` as a subprocess."""

    def __init__(self, timeout: int = 300, model: str | None = None):
        self.timeout = timeout
        self.model = model

    async def run(self, prompt: str, repo_path: str) -> RunResult:
        """Run OpenCode with a prompt in the given repo directory."""
        cmd = ["opencode", "run", prompt, "--dir", repo_path]
        if self.model:
            cmd.extend(["--model", self.model])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return RunResult(
                output=result.stdout + result.stderr,
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
