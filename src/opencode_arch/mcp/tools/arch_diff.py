"""arch_diff — native model-doc diff MCP tool over openAG.

Behavioral replacement for the legacy AMS architect_diff tool. Loads two
openAG model docs (inline YAML or, for the target, the repo's git-HEAD
model dir) and diffs them base -> target via
openag.diff.doc_diff.diff_docs: added = ids in B not A, removed = ids in A
not B. No legacy architecture_model dependency.
"""
from __future__ import annotations

import yaml

from opencode_arch.mcp._arch_tool import arch_tool


def _load_head_model(repo: str) -> dict:
    """Load the repo's ``.architecture/model`` at git HEAD; fail-soft to {}."""
    import subprocess
    import tempfile
    from pathlib import Path

    from openag.model_io import load_model_dir

    try:
        ls = subprocess.run(
            [
                "git",
                "-C",
                repo,
                "ls-tree",
                "-r",
                "--name-only",
                "HEAD",
                "--",
                ".architecture/model",
            ],
            capture_output=True,
            text=True,
        )
        if ls.returncode != 0:
            return {}
        files = [ln for ln in ls.stdout.splitlines() if ln.endswith(".v3.yaml")]
        if not files:
            return {}
        with tempfile.TemporaryDirectory() as td:
            for f in files:
                show = subprocess.run(
                    ["git", "-C", repo, "show", f"HEAD:{f}"],
                    capture_output=True,
                    text=True,
                )
                if show.returncode != 0:
                    continue
                dest = Path(td) / Path(f).name
                dest.write_text(show.stdout)
            return load_model_dir(td) or {}
    except Exception:
        return {}


@arch_tool
async def arch_diff(
    repo_path: str = "", model_a_yaml: str = "", model_b_yaml: str = ""
) -> dict:
    """Diff two architecture model docs (model_b defaults to git HEAD)."""
    from opencode_arch.mcp.envelope import resolve_repo

    resolve_repo(repo_path)

    if model_a_yaml and model_a_yaml.strip():
        doc_a = yaml.safe_load(model_a_yaml)
        if doc_a is None:
            raise ValueError("model_a_yaml is empty or not a mapping")
    else:
        from opencode_arch.mcp.tools._openag_loader import load_doc

        doc_a = load_doc(repo_path)

    if model_b_yaml and model_b_yaml.strip():
        doc_b = yaml.safe_load(model_b_yaml)
        if doc_b is None:
            raise ValueError("model_b_yaml is empty or not a mapping")
    else:
        doc_b = _load_head_model(repo_path)

    from openag.diff.doc_diff import diff_docs

    return diff_docs(doc_a, doc_b)
