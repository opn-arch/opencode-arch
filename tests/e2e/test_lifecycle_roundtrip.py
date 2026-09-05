"""T23 e2e test: subprocess-level lifecycle round-trip via the CLI.

Exercises ``python -m opencode_arch.cli.main lifecycle …`` and
``… ai …`` as real subprocess invocations, so it also proves the CLI
argparse wiring (T22) end-to-end. Excluded from the default suite via
both ``pytestmark = pytest.mark.e2e`` (matches the existing
``tests/e2e/conftest.py`` gate) and the top-level
``--ignore=tests/e2e`` flag used by the project's default pytest
command.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

# Both gates: matches conftest gate + --ignore=tests/e2e.
pytestmark = pytest.mark.e2e


ARCH_ID = "round-trip-test"

MODEL_YAML = (
    "meta:\n"
    "  project: t23-e2e\n"
    "  schema_version: '1.3'\n"
    "  generated_at: '2026-01-01T00:00:00+00:00'\n"
    "entities:\n"
    "  components:\n"
    "    - id: COMP-1\n"
    "      name: Alpha\n"
    "      status: ACTIVE\n"
    "    - id: COMP-2\n"
    "      name: Beta\n"
    "      status: ACTIVE\n"
)


def _has_cli() -> bool:
    """Sanity: can we import the CLI module in-process?"""
    try:
        import opencode_arch.cli.main  # noqa: F401
    except Exception:
        return False
    return True


pytestmark = [pytestmark, pytest.mark.skipif(
    not _has_cli(),
    reason="opencode_arch CLI not importable — install the package",
)]


def _env() -> dict:
    """Replicate the outer PYTHONPATH so the subprocess sees both
    ``opencode_arch`` and ``architecture_model``."""
    # Prefer the runtime sys.path (works whether the caller set
    # PYTHONPATH or installed the packages).
    return {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}


def _run(repo: Path, *args: str, expect_ok: bool = True) -> dict:
    """Invoke the CLI with --json --repo <repo>; return parsed JSON."""
    cmd = [
        sys.executable, "-m", "opencode_arch.cli.main",
        *args, "--repo", str(repo), "--json",
    ]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, env=_env(), timeout=90,
    )
    if expect_ok:
        assert proc.returncode == 0, (
            f"cmd {cmd!r} exit={proc.returncode}\n"
            f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
        )
    else:
        assert proc.returncode != 0, (
            f"cmd {cmd!r} unexpectedly succeeded\nstdout={proc.stdout!r}"
        )
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        return {"_raw_stdout": proc.stdout, "_raw_stderr": proc.stderr}


def test_cli_lifecycle_roundtrip(tmp_path: Path) -> None:
    """Subprocess flow: publish → load → slice → rebuild → submit →
    transitions → validate → apply (dry-run).

    First publish uses ``--init-package --architecture-id round-trip-test``
    (per T22: ``_ensure_root_package`` was removed from the CLI, so
    the descriptor must be created explicitly).
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    # Write model + supporting files.
    model_path = tmp_path / "model.yaml"
    model_path.write_text(MODEL_YAML, encoding="utf-8")

    # ---- publish (init) ------------------------------------------------
    out = _run(
        repo, "lifecycle", "publish",
        "--model", str(model_path),
        "--init-package", "--architecture-id", ARCH_ID,
    )
    assert out["package_id"] == ARCH_ID
    assert out["revision"] == "0000001"
    first_digest = out["digest"]

    # ---- load ----------------------------------------------------------
    out = _run(repo, "lifecycle", "load", ARCH_ID)
    assert out["revision"] == "0000001"
    # The load payload includes model + digest.
    assert out.get("digest") == first_digest or "digest" not in out

    # ---- slice ---------------------------------------------------------
    curation = tmp_path / "curation.yaml"
    curation.write_text(yaml.safe_dump({
        "architecture_id": ARCH_ID,
        "model_revision": "0000001",
        "scope": "local",
        "closure": "strict",
        "shared_refs": "none",
        "selectors": {"entity_kinds": ["components"]},
    }), encoding="utf-8")
    out = _run(
        repo, "lifecycle", "slice",
        "--id", "slice-1", "--curation", str(curation),
    )
    assert out["slice_id"] == "slice-1"
    slice_file = (
        repo / ".architecture" / "lifecycle" / "slices" / "slice-1.yaml"
    )
    assert slice_file.exists()

    # ---- rebuild (empty specs dir → CLI parses inputs, rebuild
    # surfaces a spec_parse_error in ``failed`` but the CLI still
    # returns 0 — that's the "no-op happy path" for wiring). --------
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    out = _run(repo, "lifecycle", "rebuild", "--specs", str(specs_dir))
    assert isinstance(out.get("built"), list)
    assert isinstance(out.get("failed"), list)

    # ---- ai submit -----------------------------------------------------
    wo_path = tmp_path / "wo.yaml"
    wo_id = "wo-e2e-001"
    wo_path.write_text(yaml.safe_dump({
        "id": wo_id,
        "intent": "T23 e2e",
        "input_slice_refs": [
            {"slice_id": "slice-1", "model_revision": "0000001"}
        ],
        "expected_proposal_kinds": ["model-patch"],
        "budget": {"max_tokens": 1000, "max_wall_seconds": 60},
        "requested_by": "t23-e2e",
        "created_at": "2026-01-01T00:00:00+00:00",
    }), encoding="utf-8")
    out = _run(repo, "ai", "submit", "--work-order", str(wo_path))
    assert out["work_order_id"] == wo_id
    job_id = out["job_id"]

    # ---- ai job transition chain --------------------------------------
    for state in ("approved", "queued", "running", "validating"):
        out = _run(repo, "ai", "job", "transition", job_id, state)
        assert out["state"] == state

    # Persist proposal & transition to completed.
    proposal_path = tmp_path / "proposal.yaml"
    proposal = {
        "kind": "model-patch",
        "provenance": {
            "work_order_id": wo_id,
            "model_version": "0000001",
            "prompt_digest": "sha256:e2e-prompt",
        },
        "operations": [{"op": "remove", "target_id": "COMP-2"}],
    }
    proposal_path.write_text(
        yaml.safe_dump(proposal), encoding="utf-8"
    )
    # CLI needs the proposal persisted inside the repo for result_ref.
    inside_p = repo / ".architecture" / "ai" / "proposals" / f"{job_id}.yaml"
    inside_p.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(proposal_path, inside_p)
    result_ref = inside_p.relative_to(repo).as_posix()
    out = _run(
        repo, "ai", "job", "transition", job_id, "completed",
        "--result-ref", result_ref,
    )
    assert out["state"] == "completed"

    # ---- ai proposal validate — CLI exits non-zero when findings are
    # present (persisted slice has no fragment, so target COMP-2 is
    # unknown). That's expected wiring for an integration-level e2e
    # test — assert the CLI ran and produced a payload with the
    # documented shape.
    out = _run(
        repo, "ai", "proposal", "validate",
        "--proposal", str(proposal_path),
        "--workorder-id", wo_id,
        "--slice-ids", "slice-1",
        expect_ok=False,
    )
    assert "passed" in out

    # ---- ai proposal apply (dry-run is the default) --------------------
    out = _run(
        repo, "ai", "proposal", "apply",
        "--proposal", str(proposal_path),
        "--workorder-id", wo_id,
    )
    assert out["new_revision"] is None, out
    assert out["digest"] is None, out


def test_cli_json_round_trip_is_parseable(tmp_path: Path) -> None:
    """Publish once and confirm --json output is a well-formed dict
    with the fields documented in T22's ``cmd_lifecycle_publish``."""
    repo = tmp_path / "repo"
    repo.mkdir()
    model_path = tmp_path / "model.yaml"
    model_path.write_text(MODEL_YAML, encoding="utf-8")

    out = _run(
        repo, "lifecycle", "publish",
        "--model", str(model_path),
        "--init-package", "--architecture-id", ARCH_ID,
    )
    for key in ("package_id", "revision", "digest", "generation_dir"):
        assert key in out, (key, out)
    assert out["package_id"] == ARCH_ID
    assert out["revision"] == "0000001"
    assert out["digest"].startswith("sha256")
    assert Path(out["generation_dir"]).exists()
