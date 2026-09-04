"""Tests for opencode_arch.lifecycle_exec.paths."""
from pathlib import Path

import pytest

from opencode_arch.lifecycle_exec import paths as P


def test_package_root_creates_directory(tmp_path):
    p = P.package_root(tmp_path)
    assert p == tmp_path / ".architecture" / "lifecycle"
    assert p.is_dir()


def test_package_index_path_creates_parent_dir_only(tmp_path):
    p = P.package_index_path(tmp_path)
    assert p == tmp_path / ".architecture" / "lifecycle" / "index.yaml"
    assert p.parent.is_dir()
    assert not p.exists()


def test_slice_dir_creates(tmp_path):
    p = P.slice_dir(tmp_path)
    assert p == tmp_path / ".architecture" / "lifecycle" / "slices"
    assert p.is_dir()


def test_view_dir_creates(tmp_path):
    p = P.view_dir(tmp_path)
    assert p == tmp_path / ".architecture" / "lifecycle" / "views"
    assert p.is_dir()


def test_artifact_dir_creates(tmp_path):
    p = P.artifact_dir(tmp_path)
    assert p == tmp_path / ".architecture" / "lifecycle" / "artifacts"
    assert p.is_dir()


def test_artifact_spec_dir_creates(tmp_path):
    p = P.artifact_spec_dir(tmp_path)
    assert p == tmp_path / ".architecture" / "lifecycle" / "artifact_specs"
    assert p.is_dir()


def test_workorder_dir_creates(tmp_path):
    p = P.workorder_dir(tmp_path)
    assert p == tmp_path / ".architecture" / "ai" / "workorders"
    assert p.is_dir()


def test_job_dir_creates(tmp_path):
    p = P.job_dir(tmp_path)
    assert p == tmp_path / ".architecture" / "ai" / "jobs"
    assert p.is_dir()


def test_proposal_dir_creates(tmp_path):
    p = P.proposal_dir(tmp_path)
    assert p == tmp_path / ".architecture" / "ai" / "proposals"
    assert p.is_dir()


def test_journal_path_creates_parent_only(tmp_path):
    p = P.journal_path(tmp_path)
    assert p == tmp_path / ".architecture" / "lifecycle" / "journal.jsonl"
    assert p.parent.is_dir()
    assert not p.exists()


def test_idempotent_creation(tmp_path):
    accessors = [
        P.package_root, P.slice_dir, P.view_dir, P.artifact_dir,
        P.artifact_spec_dir, P.workorder_dir, P.job_dir, P.proposal_dir,
    ]
    for fn in accessors:
        results = [fn(tmp_path) for _ in range(3)]
        assert results[0] == results[1] == results[2]
        assert results[0].is_dir()


def test_ensure_all_returns_dict_of_paths(tmp_path):
    result = P.ensure_all(tmp_path)
    expected_keys = {
        "package_root", "slice_dir", "view_dir", "artifact_dir",
        "artifact_spec_dir", "workorder_dir", "job_dir", "proposal_dir",
    }
    assert set(result.keys()) == expected_keys
    for name, path in result.items():
        assert isinstance(path, Path)
        assert path.is_dir(), f"{name} -> {path} not a dir"


def test_ensure_all_does_not_create_files(tmp_path):
    P.ensure_all(tmp_path)
    assert not P.package_index_path(tmp_path).exists()
    assert not P.journal_path(tmp_path).exists()


def test_paths_absolute_when_repo_absolute(tmp_path):
    assert tmp_path.is_absolute()
    for fn in [P.package_root, P.slice_dir, P.view_dir, P.artifact_dir,
               P.artifact_spec_dir, P.workorder_dir, P.job_dir, P.proposal_dir]:
        assert fn(tmp_path).is_absolute()
    assert P.package_index_path(tmp_path).is_absolute()
    assert P.journal_path(tmp_path).is_absolute()


def test_compose_path_pure_no_disk_touch():
    # Pure composition should not touch disk
    fake = Path("/nonexistent-xyz-123")
    p = P._compose_path(fake)
    assert str(p) == "/nonexistent-xyz-123/.architecture/lifecycle"
    assert not Path("/nonexistent-xyz-123").exists()


def test_constants():
    assert P.LIFECYCLE_ROOT_NAME == ".architecture/lifecycle"
    assert P.AI_ROOT_NAME == ".architecture/ai"
