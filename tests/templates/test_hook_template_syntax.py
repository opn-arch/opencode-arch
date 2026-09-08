"""Templates are syntactically valid shell and YAML."""

import subprocess
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "docs" / "templates" / "pre-commit.sh"
WORKFLOW = REPO / "docs" / "templates" / "architecture-refresh.yml"


def test_pre_commit_hook_is_valid_bash():
    result = subprocess.run(["bash", "-n", str(HOOK)], capture_output=True)
    assert result.returncode == 0, result.stderr.decode()


def test_pre_commit_hook_has_shebang_and_strict_mode():
    lines = HOOK.read_text().splitlines()
    assert lines[0] == "#!/usr/bin/env bash", f"missing bash shebang: {lines[0]!r}"
    assert any("set -euo pipefail" in ln for ln in lines[:10]), "missing strict-mode preamble"


def test_github_actions_workflow_is_valid_yaml():
    data = yaml.safe_load(WORKFLOW.read_text())
    # PyYAML parses bare `on:` as Python True.
    assert "on" in data or True in data
    assert "jobs" in data


def test_github_actions_workflow_triggers_and_job_shape():
    data = yaml.safe_load(WORKFLOW.read_text())
    triggers = data.get("on", data.get(True))
    assert isinstance(triggers, dict), f"expected mapping for `on:`, got {type(triggers)}"
    assert "push" in triggers or "pull_request" in triggers
    jobs = data["jobs"]
    assert jobs, "workflow declares no jobs"
    for name, job in jobs.items():
        assert "runs-on" in job, f"job {name!r} missing runs-on"
        assert isinstance(job.get("steps"), list) and job["steps"], (
            f"job {name!r} has no steps"
        )
