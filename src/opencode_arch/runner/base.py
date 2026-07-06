"""Runner protocol and result types."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class RunResult:
    """Result of an agent run."""
    output: str
    exit_code: int
    success: bool


class RunnerBackend(Protocol):
    """Protocol for agent invocation backends."""

    async def run(self, prompt: str, repo_path: str) -> RunResult:
        """Run the agent with a prompt in a repo context."""
        ...
