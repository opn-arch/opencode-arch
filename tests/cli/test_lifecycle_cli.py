"""Tests for lifecycle + AI CLI subcommands (T22).

Handlers are exercised both directly (with a hand-built Namespace) and
via ``main()`` with sys.argv monkeypatched (for --help / dispatch wiring).
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import pytest
import yaml

from architecture_model.ai.jobs import JobState, JobStore
from architecture_model.lifecycle.package import load_package
from architecture_model.lifecycle.publication import PackageBundle, publish
from architecture_model.lifecycle.versions import SchemaVersions


MODEL_YAML = (
    "meta:\n"
    "  project: t22\n"
    "  schema_version: '1.3'\n"
    "entities:\n"
    "  components:\n"
    "    - id: COMP-1\n"
    "      name: One\n"
    "      status: ACTIVE\n"
)


def _write_root_pkg(repo: Path) -> Path:
    lc = repo / ".architecture" / "lifecycle"
    lc.mkdir(parents=True, exist_ok=True)
    (lc / "package.yaml").write_text(
        yaml.safe_dump(
            {
                "architecture_id": "root-pkg",
                "name": "Root",
                "slug": "root-pkg",
                "contract_version": SchemaVersions.PACKAGE,
                "model_ref": "model/.architecture-model.yaml",
                "manifest_ref": "manifest/manifest.json",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return lc


def _publish_initial(repo: Path):
    lc = _write_root_pkg(repo)
    pkg = load_package(lc)
    res = publish(
        pkg,
        PackageBundle(model_bytes=MODEL_YAML.encode("utf-8"), manifest_bytes=b"{}"),
    )
    return pkg, res


def _ns(**kwargs) -> argparse.Namespace:
    kwargs.setdefault("json", False)
    return argparse.Namespace(**kwargs)


def _run_main(argv, monkeypatch):
    from opencode_arch.cli import main as main_mod

    monkeypatch.setattr(sys, "argv", ["opencode-arch"] + argv)
    try:
        main_mod.main()
        return 0
    except SystemExit as e:
        return 0 if e.code is None else int(e.code)


# --------------------------------------------------------------- --help wiring


@pytest.mark.parametrize(
    "argv",
    [
        ["lifecycle", "--help"],
        ["lifecycle", "publish", "--help"],
        ["lifecycle", "load", "--help"],
        ["lifecycle", "stale", "--help"],
        ["lifecycle", "slice", "--help"],
        ["lifecycle", "rebuild", "--help"],
        ["lifecycle", "merge", "--help"],
        ["ai", "--help"],
        ["ai", "submit", "--help"],
        ["ai", "job", "get", "--help"],
        ["ai", "job", "transition", "--help"],
        ["ai", "proposal", "validate", "--help"],
        ["ai", "proposal", "apply", "--help"],
    ],
)
def test_help_exits_zero(argv, monkeypatch, capsys):
    rc = _run_main(argv, monkeypatch)
    assert rc == 0
    out = capsys.readouterr().out
    assert "usage" in out.lower()


# --------------------------------------------------------------- lifecycle.publish


def test_lifecycle_publish_happy_human(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_lifecycle_publish

    model_file = tmp_path / "m.yaml"
    model_file.write_text(MODEL_YAML)
    ns = _ns(
        model=str(model_file),
        manifest=None,
        parent=None,
        repo=str(tmp_path),
        init_package=True,
        architecture_id="root-pkg",
        package_name=None,
    )
    rc = cmd_lifecycle_publish(ns)
    assert rc == 0
    out = capsys.readouterr().out
    assert "0000001" in out


def test_lifecycle_publish_json(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_lifecycle_publish

    model_file = tmp_path / "m.yaml"
    model_file.write_text(MODEL_YAML)
    ns = _ns(
        model=str(model_file),
        manifest=None,
        parent=None,
        repo=str(tmp_path),
        json=True,
        init_package=True,
        architecture_id="root-pkg",
        package_name=None,
    )
    rc = cmd_lifecycle_publish(ns)
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["revision"] == "0000001"
    assert payload["package_id"] == "root-pkg"
    assert payload["digest"]


def test_lifecycle_publish_bad_parent_exit_1(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_lifecycle_publish

    _write_root_pkg(tmp_path)  # pre-existing package so parent check is reached
    model_file = tmp_path / "m.yaml"
    model_file.write_text(MODEL_YAML)
    ns = _ns(model=str(model_file), manifest=None, parent="nope", repo=str(tmp_path))
    rc = cmd_lifecycle_publish(ns)
    assert rc == 1


# --------------------------------------------------------------- publish safety (C-2)


def test_publish_no_package_returns_not_found(tmp_path, capsys):
    """Publish in a fresh repo (no package.yaml, no --init-package) → exit 1."""
    from opencode_arch.cli.lifecycle import cmd_lifecycle_publish

    model_file = tmp_path / "m.yaml"
    model_file.write_text(MODEL_YAML)
    ns = _ns(model=str(model_file), manifest=None, parent=None, repo=str(tmp_path))
    rc = cmd_lifecycle_publish(ns)
    assert rc == 1
    assert "Package not found" in capsys.readouterr().err
    # And nothing got written.
    assert not (tmp_path / ".architecture" / "lifecycle" / "package.yaml").exists()


def test_publish_init_package_creates_with_provided_id(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_lifecycle_publish

    model_file = tmp_path / "m.yaml"
    model_file.write_text(MODEL_YAML)
    ns = _ns(
        model=str(model_file),
        manifest=None,
        parent=None,
        repo=str(tmp_path),
        init_package=True,
        architecture_id="my-pkg",
        package_name=None,
    )
    rc = cmd_lifecycle_publish(ns)
    assert rc == 0
    pkg_yaml = tmp_path / ".architecture" / "lifecycle" / "package.yaml"
    assert pkg_yaml.exists()
    data = yaml.safe_load(pkg_yaml.read_text())
    assert data["architecture_id"] == "my-pkg"


def test_publish_init_package_without_id_fails_usage(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_lifecycle_publish

    model_file = tmp_path / "m.yaml"
    model_file.write_text(MODEL_YAML)
    ns = _ns(
        model=str(model_file),
        manifest=None,
        parent=None,
        repo=str(tmp_path),
        init_package=True,
        architecture_id=None,
        package_name=None,
    )
    rc = cmd_lifecycle_publish(ns)
    assert rc in (1, 2)
    err = capsys.readouterr().err.lower()
    assert "architecture-id" in err or "architecture_id" in err


def test_publish_init_package_when_already_exists_fails(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_lifecycle_publish

    lc = _write_root_pkg(tmp_path)
    pkg_yaml = lc / "package.yaml"
    original = pkg_yaml.read_text()

    model_file = tmp_path / "m.yaml"
    model_file.write_text(MODEL_YAML)
    ns = _ns(
        model=str(model_file),
        manifest=None,
        parent=None,
        repo=str(tmp_path),
        init_package=True,
        architecture_id="something-else",
        package_name=None,
    )
    rc = cmd_lifecycle_publish(ns)
    assert rc == 1
    err = capsys.readouterr().err.lower()
    assert "already" in err
    # No clobber.
    assert pkg_yaml.read_text() == original


def test_publish_parent_check_runs_before_any_write(tmp_path, capsys):
    """Init scenario with bad --parent must exit 1 and write no package.yaml."""
    from opencode_arch.cli.lifecycle import cmd_lifecycle_publish

    model_file = tmp_path / "m.yaml"
    model_file.write_text(MODEL_YAML)
    ns = _ns(
        model=str(model_file),
        manifest=None,
        parent="nope",
        repo=str(tmp_path),
        init_package=True,
        architecture_id="my-pkg",
        package_name=None,
    )
    rc = cmd_lifecycle_publish(ns)
    assert rc == 1
    assert not (tmp_path / ".architecture" / "lifecycle" / "package.yaml").exists()


# --------------------------------------------------------------- lifecycle.load


def test_lifecycle_load_in_repo(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_lifecycle_load

    _publish_initial(tmp_path)
    ns = _ns(package_id="root-pkg", revision=None, repo=str(tmp_path), federated=False, json=True)
    rc = cmd_lifecycle_load(ns)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["revision"] == "0000001"


def test_lifecycle_load_bad_revision_format_exit_2(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_lifecycle_load

    _publish_initial(tmp_path)
    ns = _ns(package_id="root-pkg", revision="bad", repo=str(tmp_path), federated=False)
    rc = cmd_lifecycle_load(ns)
    assert rc == 2


def test_lifecycle_load_missing_generation_exit_1(tmp_path):
    from opencode_arch.cli.lifecycle import cmd_lifecycle_load

    _publish_initial(tmp_path)
    ns = _ns(package_id="root-pkg", revision="9999999", repo=str(tmp_path), federated=False)
    rc = cmd_lifecycle_load(ns)
    assert rc == 1


def test_lifecycle_load_federated(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_lifecycle_load
    from opencode_arch.lifecycle_exec.federation import FederatedRegistry

    _publish_initial(tmp_path)
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(tmp_path / ".architecture" / "lifecycle")

    ns = _ns(
        package_id="root-pkg",
        revision=None,
        repo=str(tmp_path),
        federated=True,
        json=True,
    )
    rc = cmd_lifecycle_load(ns, _registry=reg)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["package_id"] == "root-pkg"


def test_lifecycle_load_federated_not_found_exit_1(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_lifecycle_load
    from opencode_arch.lifecycle_exec.federation import FederatedRegistry

    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    reg = FederatedRegistry(config_dir=cfg_dir)
    ns = _ns(
        package_id="nope", revision=None, repo=str(tmp_path), federated=True
    )
    rc = cmd_lifecycle_load(ns, _registry=reg)
    assert rc == 1


# --------------------------------------------------------------- lifecycle.stale


def test_lifecycle_stale_prints_nodes(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_lifecycle_stale

    _publish_initial(tmp_path)
    ns = _ns(repo=str(tmp_path), json=True)
    rc = cmd_lifecycle_stale(ns)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload["nodes"], list)
    assert any(n["kind"] == "package" for n in payload["nodes"])


# --------------------------------------------------------------- lifecycle.slice


def test_lifecycle_slice_writes_file(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_lifecycle_slice

    _publish_initial(tmp_path)
    curation = {
        "id": "my-slice",
        "architecture_id": "root-pkg",
        "model_revision": "0000001",
        "scope": "local",
        "closure": "strict",
        "shared_refs": "none",
        "selectors": {"entity_ids": ["COMP-1"]},
    }
    curation_file = tmp_path / "curation.yaml"
    curation_file.write_text(yaml.safe_dump(curation))
    ns = _ns(
        id="my-slice",
        curation=str(curation_file),
        repo=str(tmp_path),
        json=True,
    )
    rc = cmd_lifecycle_slice(ns)
    assert rc == 0
    target = tmp_path / ".architecture" / "lifecycle" / "slices" / "my-slice.yaml"
    assert target.exists()


# --------------------------------------------------------------- lifecycle.rebuild


def test_lifecycle_rebuild_invokes_fake(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_lifecycle_rebuild
    from opencode_arch.lifecycle_exec.rebuild import RebuildReport

    specs_dir = tmp_path / "specs"
    (specs_dir / "artifacts").mkdir(parents=True)
    (specs_dir / "artifacts" / "a1.yaml").write_text("id: a1\n")

    called = {}

    def fake_rebuild(repo, arts, views, slices, force=False):
        called["arts"] = arts
        called["force"] = force
        return RebuildReport(built=[{"id": "a1"}])

    ns = _ns(specs=str(specs_dir), force=True, repo=str(tmp_path), json=True)
    rc = cmd_lifecycle_rebuild(ns, _rebuild=fake_rebuild)
    assert rc == 0
    assert called["force"] is True
    assert called["arts"] == [{"id": "a1"}]


# --------------------------------------------------------------- lifecycle.merge


def _publish_more(pkg, model_yaml_str):
    return publish(
        pkg,
        PackageBundle(
            model_bytes=model_yaml_str.encode("utf-8"), manifest_bytes=b"{}"
        ),
    )


def test_lifecycle_merge_bad_revision_format_exit_2(tmp_path):
    from opencode_arch.cli.lifecycle import cmd_lifecycle_merge

    _publish_initial(tmp_path)
    ns = _ns(base="1", local="0000001", remote="0000001", repo=str(tmp_path))
    rc = cmd_lifecycle_merge(ns)
    assert rc == 2


def test_lifecycle_merge_no_conflicts_publishes(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_lifecycle_merge
    from opencode_arch.lifecycle_exec.merge import MergeResult
    from architecture_model.core.parser import _parse_raw

    _publish_initial(tmp_path)
    parsed = _parse_raw(yaml.safe_load(MODEL_YAML))

    def fake_merge(base, local, remote):
        return MergeResult(
            merged_model=parsed,
            conflicts=[],
            stats={"entities_auto_merged": 1},
        )

    ns = _ns(
        base="0000001",
        local="0000001",
        remote="0000001",
        repo=str(tmp_path),
        json=True,
    )
    rc = cmd_lifecycle_merge(ns, _merge=fake_merge)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["merged"] is True
    assert payload["merged_revision"] == "0000002"


def test_lifecycle_merge_conflicts_exit_1(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_lifecycle_merge
    from opencode_arch.lifecycle_exec.merge import Conflict, MergeResult
    from architecture_model.core.parser import _parse_raw

    _publish_initial(tmp_path)
    parsed = _parse_raw(yaml.safe_load(MODEL_YAML))

    def fake_merge(base, local, remote):
        return MergeResult(
            merged_model=parsed,
            conflicts=[Conflict(entity_id="COMP-1", field="name", base="a", local="b", remote="c")],
            stats={"entities_added_local": 0},
        )

    ns = _ns(
        base="0000001",
        local="0000001",
        remote="0000001",
        repo=str(tmp_path),
        json=True,
    )
    rc = cmd_lifecycle_merge(ns, _merge=fake_merge)
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["merged"] is False
    assert len(payload["conflicts"]) == 1


# --------------------------------------------------------------- ai.submit


def _valid_work_order_dict() -> dict:
    return {
        "id": "wo-cli-1",
        "intent": "Assess CLI wiring",
        "input_slice_refs": [
            {"slice_id": "sl-1", "model_revision": "0000001"}
        ],
        "expected_proposal_kinds": ["model-patch"],
        "budget": {"max_tokens": 1000, "max_wall_seconds": 60},
        "requested_by": "tester",
        "created_at": "2026-01-01T00:00:00Z",
    }


def test_ai_submit_happy(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_ai_submit

    wo_file = tmp_path / "wo.yaml"
    wo_file.write_text(yaml.safe_dump(_valid_work_order_dict()))
    ns = _ns(work_order=str(wo_file), repo=str(tmp_path), json=True)
    rc = cmd_ai_submit(ns)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["work_order_id"] == "wo-cli-1"
    assert payload["job_id"]


def test_ai_submit_duplicate_exit_1(tmp_path):
    from opencode_arch.cli.lifecycle import cmd_ai_submit

    wo_file = tmp_path / "wo.yaml"
    wo_file.write_text(yaml.safe_dump(_valid_work_order_dict()))
    ns = _ns(work_order=str(wo_file), repo=str(tmp_path))
    assert cmd_ai_submit(ns) == 0
    ns2 = _ns(work_order=str(wo_file), repo=str(tmp_path))
    assert cmd_ai_submit(ns2) == 1


# --------------------------------------------------------------- ai.job.get / transition


def test_ai_job_get_happy(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_ai_job_get, cmd_ai_submit

    wo_file = tmp_path / "wo.yaml"
    wo_file.write_text(yaml.safe_dump(_valid_work_order_dict()))
    ns = _ns(work_order=str(wo_file), repo=str(tmp_path), json=True)
    assert cmd_ai_submit(ns) == 0
    job_id = json.loads(capsys.readouterr().out)["job_id"]

    ns2 = _ns(job_id=job_id, repo=str(tmp_path), json=True)
    rc = cmd_ai_job_get(ns2)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == job_id


def test_ai_job_get_missing_exit_1(tmp_path):
    from opencode_arch.cli.lifecycle import cmd_ai_job_get

    (tmp_path / ".architecture" / "ai").mkdir(parents=True)
    ns = _ns(job_id="nope", repo=str(tmp_path))
    assert cmd_ai_job_get(ns) == 1


def test_ai_job_transition_happy(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_ai_job_transition, cmd_ai_submit

    wo_file = tmp_path / "wo.yaml"
    wo_file.write_text(yaml.safe_dump(_valid_work_order_dict()))
    ns = _ns(work_order=str(wo_file), repo=str(tmp_path), json=True)
    assert cmd_ai_submit(ns) == 0
    job_id = json.loads(capsys.readouterr().out)["job_id"]

    ns2 = _ns(
        job_id=job_id,
        new_state="approved",
        result_ref=None,
        error=None,
        repo=str(tmp_path),
        json=True,
    )
    rc = cmd_ai_job_transition(ns2)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["state"] == "approved"


def test_ai_job_transition_invalid_state_exit_2(tmp_path):
    from opencode_arch.cli.lifecycle import cmd_ai_job_transition

    (tmp_path / ".architecture" / "ai").mkdir(parents=True)
    ns = _ns(
        job_id="x",
        new_state="not-a-state",
        result_ref=None,
        error=None,
        repo=str(tmp_path),
    )
    assert cmd_ai_job_transition(ns) == 2


def test_ai_job_transition_invalid_transition_exit_1(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_ai_job_transition, cmd_ai_submit

    wo_file = tmp_path / "wo.yaml"
    wo_file.write_text(yaml.safe_dump(_valid_work_order_dict()))
    ns = _ns(work_order=str(wo_file), repo=str(tmp_path), json=True)
    cmd_ai_submit(ns)
    job_id = json.loads(capsys.readouterr().out)["job_id"]

    # queued → completed is invalid.
    ns2 = _ns(
        job_id=job_id,
        new_state="completed",
        result_ref="r",
        error=None,
        repo=str(tmp_path),
    )
    assert cmd_ai_job_transition(ns2) == 1


# --------------------------------------------------------------- ai.proposal.validate


def _make_slice(tmp_path: Path, sid: str) -> None:
    d = tmp_path / ".architecture" / "lifecycle" / "slices"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{sid}.yaml").write_text(
        yaml.safe_dump({"id": sid, "architecture_id": "root-pkg"})
    )


def _submit_wo(tmp_path: Path) -> str:
    from opencode_arch.cli.lifecycle import cmd_ai_submit

    wo_file = tmp_path / "wo.yaml"
    wo_file.write_text(yaml.safe_dump(_valid_work_order_dict()))
    ns = _ns(work_order=str(wo_file), repo=str(tmp_path), json=True)
    cmd_ai_submit(ns)
    return "wo-cli-1"


def test_ai_proposal_validate_malformed_exit_1(tmp_path):
    from opencode_arch.cli.lifecycle import cmd_ai_proposal_validate

    p = tmp_path / "prop.yaml"
    p.write_text("kind: not-a-real-kind\n")
    _submit_wo(tmp_path)
    ns = _ns(
        proposal=str(p),
        workorder_id="wo-cli-1",
        slice_ids="sl-1",
        repo=str(tmp_path),
    )
    rc = cmd_ai_proposal_validate(ns)
    assert rc == 1


def test_ai_proposal_validate_missing_workorder_exit_1(tmp_path):
    from opencode_arch.cli.lifecycle import cmd_ai_proposal_validate

    p = tmp_path / "prop.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "kind": "impact-assessment",
                "provenance": {
                    "work_order_id": "wo-cli-1",
                    "model_version": "sha256:x",
                    "prompt_digest": "sha256:y",
                },
                "affected_ids": [],
                "summary": "",
            }
        )
    )
    ns = _ns(
        proposal=str(p),
        workorder_id="wo-missing",
        slice_ids="sl-1",
        repo=str(tmp_path),
    )
    assert cmd_ai_proposal_validate(ns) == 1


# --------------------------------------------------------------- ai.proposal.apply


def _impact_proposal_dict() -> dict:
    return {
        "kind": "impact-assessment",
        "provenance": {
            "work_order_id": "wo-cli-1",
            "model_version": "sha256:x",
            "prompt_digest": "sha256:y",
        },
        "affected_ids": [],
        "summary": "hi",
    }


def test_ai_proposal_apply_dry_run(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_ai_proposal_apply

    p = tmp_path / "prop.yaml"
    p.write_text(yaml.safe_dump(_impact_proposal_dict()))
    ns = _ns(
        proposal=str(p),
        workorder_id="wo-cli-1",
        dry_run=True,
        repo=str(tmp_path),
        json=True,
    )
    rc = cmd_ai_proposal_apply(ns)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["new_revision"] is None


def test_ai_proposal_apply_drift_error(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_ai_proposal_apply
    from opencode_arch.lifecycle_exec.apply import DriftError

    p = tmp_path / "prop.yaml"
    p.write_text(yaml.safe_dump(_impact_proposal_dict()))

    def bad(*a, **k):
        raise DriftError(expected="a", actual="b")

    ns = _ns(
        proposal=str(p),
        workorder_id="wo-cli-1",
        dry_run=False,
        repo=str(tmp_path),
    )
    rc = cmd_ai_proposal_apply(ns, _apply=bad)
    assert rc == 1
    err = capsys.readouterr().err
    assert "Drift detected" in err


def test_ai_proposal_apply_invalid_proposal_error(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_ai_proposal_apply
    from opencode_arch.lifecycle_exec.apply import InvalidProposalError

    p = tmp_path / "prop.yaml"
    p.write_text(yaml.safe_dump(_impact_proposal_dict()))

    def bad(*a, **k):
        raise InvalidProposalError("bad shape")

    ns = _ns(
        proposal=str(p),
        workorder_id="wo-cli-1",
        dry_run=False,
        repo=str(tmp_path),
    )
    rc = cmd_ai_proposal_apply(ns, _apply=bad)
    assert rc == 1
    assert "Invalid proposal" in capsys.readouterr().err


def test_ai_proposal_apply_package_not_found(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_ai_proposal_apply
    from opencode_arch.lifecycle_exec.apply import PackageNotFoundError

    p = tmp_path / "prop.yaml"
    p.write_text(yaml.safe_dump(_impact_proposal_dict()))

    def bad(*a, **k):
        raise PackageNotFoundError("missing")

    ns = _ns(
        proposal=str(p),
        workorder_id="wo-cli-1",
        dry_run=False,
        repo=str(tmp_path),
    )
    rc = cmd_ai_proposal_apply(ns, _apply=bad)
    assert rc == 1
    assert "Package not found" in capsys.readouterr().err


def test_ai_proposal_apply_federation_not_found(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_ai_proposal_apply
    from opencode_arch.lifecycle_exec.federation import PackageNotFoundInFederationError

    p = tmp_path / "prop.yaml"
    p.write_text(yaml.safe_dump(_impact_proposal_dict()))

    def bad(*a, **k):
        raise PackageNotFoundInFederationError("x", [])

    ns = _ns(
        proposal=str(p),
        workorder_id="wo-cli-1",
        dry_run=False,
        repo=str(tmp_path),
    )
    rc = cmd_ai_proposal_apply(ns, _apply=bad)
    assert rc == 1
    assert "Package not found in federation" in capsys.readouterr().err


def test_ai_proposal_apply_unknown_exit_3(tmp_path, capsys):
    from opencode_arch.cli.lifecycle import cmd_ai_proposal_apply

    p = tmp_path / "prop.yaml"
    p.write_text(yaml.safe_dump(_impact_proposal_dict()))

    def bad(*a, **k):
        raise RuntimeError("boom!\nline2")

    ns = _ns(
        proposal=str(p),
        workorder_id="wo-cli-1",
        dry_run=False,
        repo=str(tmp_path),
    )
    rc = cmd_ai_proposal_apply(ns, _apply=bad)
    assert rc == 3
    err = capsys.readouterr().err
    assert "Internal error" in err
    # No traceback leak.
    assert "line2" not in err


# --------------------------------------------------------------- apply dry-run default (C-1)


def _fake_apply_report():
    import dataclasses

    @dataclasses.dataclass
    class R:
        new_revision: object = None
        passed: bool = True

    return R()


def test_ai_proposal_apply_default_is_dry_run(tmp_path, monkeypatch, capsys):
    """Without --apply, the CLI must default to dry_run=True (safe)."""
    p = tmp_path / "prop.yaml"
    p.write_text(yaml.safe_dump(_impact_proposal_dict()))

    seen = {}

    def fake(repo, proposal, *, dry_run):
        seen["dry_run"] = dry_run
        return _fake_apply_report()

    import opencode_arch.lifecycle_exec.apply as _apply_mod

    monkeypatch.setattr(_apply_mod, "apply_proposal", fake)

    rc = _run_main(
        [
            "ai", "proposal", "apply",
            "--proposal", str(p),
            "--workorder-id", "wo-cli-1",
            "--repo", str(tmp_path),
            "--json",
        ],
        monkeypatch,
    )
    assert rc == 0
    assert seen.get("dry_run") is True


def test_ai_proposal_apply_apply_flag_disables_dry_run(tmp_path, monkeypatch, capsys):
    """Passing --apply must flip dry_run to False."""
    p = tmp_path / "prop.yaml"
    p.write_text(yaml.safe_dump(_impact_proposal_dict()))

    seen = {}

    def fake(repo, proposal, *, dry_run):
        seen["dry_run"] = dry_run
        return _fake_apply_report()

    import opencode_arch.lifecycle_exec.apply as _apply_mod

    monkeypatch.setattr(_apply_mod, "apply_proposal", fake)

    rc = _run_main(
        [
            "ai", "proposal", "apply",
            "--proposal", str(p),
            "--workorder-id", "wo-cli-1",
            "--repo", str(tmp_path),
            "--apply",
            "--json",
        ],
        monkeypatch,
    )
    assert rc == 0
    assert seen.get("dry_run") is False


def test_ai_proposal_apply_help_documents_default(monkeypatch, capsys):
    """--help must mention dry-run behavior and default."""
    rc = _run_main(["ai", "proposal", "apply", "--help"], monkeypatch)
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "dry-run" in out or "dry run" in out
    assert "default" in out


# --------------------------------------------------------------- slice-ids parsing


def test_parse_slice_ids_valid():
    from opencode_arch.cli.lifecycle import _parse_slice_ids

    assert _parse_slice_ids("a, b ,c") == ["a", "b", "c"]


def test_parse_slice_ids_empty_entry_raises():
    from opencode_arch.cli.lifecycle import _parse_slice_ids

    with pytest.raises(argparse.ArgumentTypeError):
        _parse_slice_ids("a,,b")


# --------------------------------------------------------------- main() dispatch


def test_main_dispatch_lifecycle_stale(tmp_path, monkeypatch, capsys):
    _publish_initial(tmp_path)
    rc = _run_main(["lifecycle", "stale", "--repo", str(tmp_path), "--json"], monkeypatch)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "nodes" in payload
