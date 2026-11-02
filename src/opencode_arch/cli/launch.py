"""Launch an architecture-aware OpenCode session.

Thin launcher: resolve the target repo, verify ``opencode`` is on PATH, then
exec it. The ``opencode-arch`` MCP server is registered in the user's OpenCode
config, so the spawned session automatically has the ``arch_*`` (openAG-backed)
tools available alongside normal OpenCode functionality.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def run_launch(repo_path: str | None = None, skip_exec: bool = False) -> dict:
    """Launch an interactive OpenCode session in ``repo_path``.

    Args:
        repo_path: Target repository (default: current directory).
        skip_exec: If True, run resolution/validation only and return a dict
            instead of exec'ing (for testing).

    Returns:
        ``{"repo": ..., "opencode": ...}`` when ``skip_exec`` is True.

    Exits:
        Non-zero via ``sys.exit`` when the directory is invalid or ``opencode``
        is not found on PATH.
    """
    repo = Path(repo_path or ".").resolve()
    if not repo.is_dir():
        print(f"Error: {repo} is not a directory", file=sys.stderr)
        sys.exit(1)

    opencode_bin = shutil.which("opencode")
    if not opencode_bin:
        print("Error: 'opencode' not found in PATH. Install OpenCode first.", file=sys.stderr)
        print("  See: https://opencode.ai", file=sys.stderr)
        sys.exit(1)

    if skip_exec:
        return {"repo": str(repo), "opencode": opencode_bin}

    os.chdir(repo)
    os.execvp(opencode_bin, [opencode_bin])
