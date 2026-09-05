"""Tests for FederatedRegistry (T21)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

from opencode_arch.lifecycle_exec.federation import (
    AmbiguousPackageError,
    FederatedRegistry,
    FederationConfigError,
    FederationError,
    PackageDescriptor,
    PackageNotFoundInFederationError,
    RevisionNotFoundError,
)


# --- fixtures / helpers ------------------------------------------------------

def _make_package(
    root: Path,
    rel: str,
    pkg_id: str,
    *,
    generations: list[tuple[str, str | None]] | None = None,
    current: str | None = None,
) -> Path:
    """Create a fake published package under ``root/rel``.

    ``generations`` is a list of ``(revname, root_digest_or_None)`` pairs.
    ``current`` (revname) creates a ``CURRENT`` symlink.
    Returns the package directory.
    """
    pkg_dir = root / rel
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "package.yaml").write_text(
        yaml.safe_dump({
            "architecture_id": pkg_id,
            "name": pkg_id,
            "slug": pkg_id,
            "contract_version": "1.0",
            "model_ref": "model.yaml",
            "manifest_ref": "manifest.json",
        }),
        encoding="utf-8",
    )
    for rev, digest in generations or []:
        gen = pkg_dir / "generations" / rev
        gen.mkdir(parents=True, exist_ok=True)
        if digest is not None:
            (gen / "digest.json").write_text(
                json.dumps({"root_digest": digest}), encoding="utf-8"
            )
    if current is not None:
        (pkg_dir / "CURRENT").symlink_to(Path("generations") / current)
    return pkg_dir


@pytest.fixture
def cfg_dir(tmp_path: Path) -> Path:
    d = tmp_path / "cfg"
    d.mkdir()
    return d


# --- add_root ----------------------------------------------------------------

def test_add_root_happy_path(cfg_dir: Path, tmp_path: Path) -> None:
    reg = FederatedRegistry(config_dir=cfg_dir)
    root = tmp_path / "reg1"
    root.mkdir()
    reg.add_root(root)
    assert reg.list_roots() == [root.resolve()]
    assert reg.config_path.is_file()


def test_add_root_nonexistent_raises(cfg_dir: Path, tmp_path: Path) -> None:
    reg = FederatedRegistry(config_dir=cfg_dir)
    with pytest.raises(ValueError, match="does not exist"):
        reg.add_root(tmp_path / "missing")


def test_add_root_file_not_dir_raises(cfg_dir: Path, tmp_path: Path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("x")
    reg = FederatedRegistry(config_dir=cfg_dir)
    with pytest.raises(ValueError, match="not a directory"):
        reg.add_root(f)


def test_add_root_idempotent(cfg_dir: Path, tmp_path: Path) -> None:
    root = tmp_path / "r"
    root.mkdir()
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(root)
    reg.add_root(root)  # no-op, no raise
    assert reg.list_roots() == [root.resolve()]


def test_add_root_resolves_symlink_and_relative(
    cfg_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(link)
    # symlink resolved to real path
    assert reg.list_roots() == [real.resolve()]


def test_add_root_persists_and_reloads(cfg_dir: Path, tmp_path: Path) -> None:
    root = tmp_path / "r"
    root.mkdir()
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(root)
    # new instance should see same roots
    reg2 = FederatedRegistry(config_dir=cfg_dir)
    assert reg2.list_roots() == [root.resolve()]


def test_add_root_atomic_no_tmp_leftover(cfg_dir: Path, tmp_path: Path) -> None:
    root = tmp_path / "r"
    root.mkdir()
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(root)
    leftovers = list(cfg_dir.glob("*.tmp"))
    assert leftovers == []


# --- remove_root -------------------------------------------------------------

def test_remove_root_happy(cfg_dir: Path, tmp_path: Path) -> None:
    root = tmp_path / "r"
    root.mkdir()
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(root)
    reg.remove_root(root)
    assert reg.list_roots() == []
    # persisted
    reg2 = FederatedRegistry(config_dir=cfg_dir)
    assert reg2.list_roots() == []


def test_remove_root_noop_on_unknown(cfg_dir: Path, tmp_path: Path) -> None:
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.remove_root(tmp_path / "never-added")  # no raise
    assert reg.list_roots() == []


# --- list_roots defensive copy -----------------------------------------------

def test_list_roots_returns_defensive_copy(cfg_dir: Path, tmp_path: Path) -> None:
    root = tmp_path / "r"
    root.mkdir()
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(root)
    got = reg.list_roots()
    got.append(Path("/tmp/bogus"))
    assert reg.list_roots() == [root.resolve()]


# --- resolve -----------------------------------------------------------------

def test_resolve_current_revision(cfg_dir: Path, tmp_path: Path) -> None:
    root = tmp_path / "reg"
    root.mkdir()
    _make_package(
        root, "pkg-a", "pkg-a",
        generations=[("0000001", "sha256:abc"), ("0000002", "sha256:def")],
        current="0000002",
    )
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(root)
    r, desc = reg.resolve("pkg-a")
    assert r == root.resolve()
    assert isinstance(desc, PackageDescriptor)
    assert desc.id == "pkg-a"
    assert desc.revision == "0000002"
    assert desc.digest == "sha256:def"
    assert desc.path.name == "package.yaml"


def test_resolve_explicit_revision(cfg_dir: Path, tmp_path: Path) -> None:
    root = tmp_path / "reg"
    root.mkdir()
    _make_package(
        root, "p", "pkg-b",
        generations=[("0000001", "sha256:aaa"), ("0000002", "sha256:bbb")],
        current="0000002",
    )
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(root)
    _r, desc = reg.resolve("pkg-b", revision="0000001")
    assert desc.revision == "0000001"
    assert desc.digest == "sha256:aaa"


def test_resolve_package_not_found(cfg_dir: Path, tmp_path: Path) -> None:
    root = tmp_path / "reg"
    root.mkdir()
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(root)
    with pytest.raises(PackageNotFoundInFederationError) as ei:
        reg.resolve("no-such-pkg")
    assert ei.value.package_id == "no-such-pkg"
    assert ei.value.searched_roots == [root.resolve()]


def test_resolve_explicit_revision_missing(cfg_dir: Path, tmp_path: Path) -> None:
    root = tmp_path / "reg"
    root.mkdir()
    _make_package(root, "p", "pkg-c", generations=[("0000001", "sha256:x")], current="0000001")
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(root)
    with pytest.raises(RevisionNotFoundError) as ei:
        reg.resolve("pkg-c", revision="0000099")
    assert ei.value.package_id == "pkg-c"
    assert ei.value.revision == "0000099"
    assert ei.value.root == root.resolve()


def test_resolve_no_current_returns_none_revision(
    cfg_dir: Path, tmp_path: Path
) -> None:
    root = tmp_path / "reg"
    root.mkdir()
    _make_package(root, "p", "unpub")  # no generations, no CURRENT
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(root)
    _r, desc = reg.resolve("unpub")
    assert desc.revision is None
    assert desc.digest is None


def test_resolve_multi_root_fifo_order(cfg_dir: Path, tmp_path: Path) -> None:
    r1 = tmp_path / "r1"
    r1.mkdir()
    r2 = tmp_path / "r2"
    r2.mkdir()
    _make_package(r1, "a", "shared-id", generations=[("0000001", "sha256:one")], current="0000001")
    _make_package(r2, "b", "shared-id", generations=[("0000001", "sha256:two")], current="0000001")
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(r1)
    reg.add_root(r2)
    root, desc = reg.resolve("shared-id")
    assert root == r1.resolve()
    assert desc.digest == "sha256:one"


def test_resolve_ambiguous_within_single_root(
    cfg_dir: Path, tmp_path: Path
) -> None:
    root = tmp_path / "reg"
    root.mkdir()
    _make_package(root, "x", "dup-id")
    _make_package(root, "y", "dup-id")
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(root)
    with pytest.raises(AmbiguousPackageError) as ei:
        reg.resolve("dup-id")
    assert ei.value.package_id == "dup-id"
    assert len(ei.value.matches) == 2


def test_resolve_skips_noise_dirs(cfg_dir: Path, tmp_path: Path) -> None:
    root = tmp_path / "reg"
    root.mkdir()
    # a valid package
    _make_package(root, "keep", "wanted", generations=[("0000001", "sha256:k")], current="0000001")
    # a package.yaml buried inside .git — must be skipped
    hidden = root / ".git" / "sneaky"
    hidden.mkdir(parents=True)
    (hidden / "package.yaml").write_text(
        yaml.safe_dump({"architecture_id": "wanted"}), encoding="utf-8"
    )
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(root)
    # Would raise AmbiguousPackageError if .git wasn't skipped
    _r, desc = reg.resolve("wanted")
    assert desc.digest == "sha256:k"


def test_resolve_caches_scan(
    cfg_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "reg"
    root.mkdir()
    _make_package(root, "p", "pkg", generations=[("0000001", "sha256:z")], current="0000001")
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(root)
    calls = {"n": 0}
    orig = reg._scan_root

    def spy(r: Path) -> dict[str, Path]:
        calls["n"] += 1
        return orig(r)

    monkeypatch.setattr(reg, "_scan_root", spy)
    reg.resolve("pkg")
    reg.resolve("pkg")
    reg.resolve("pkg")
    assert calls["n"] == 1


def test_resolve_cache_invalidated_after_add_and_remove(
    cfg_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    r1 = tmp_path / "r1"
    r1.mkdir()
    r2 = tmp_path / "r2"
    r2.mkdir()
    _make_package(r1, "p", "pkg", generations=[("0000001", "sha256:1")], current="0000001")
    _make_package(r2, "p", "pkg2", generations=[("0000001", "sha256:2")], current="0000001")
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(r1)
    reg.resolve("pkg")
    # add_root should invalidate cache
    calls = {"n": 0}
    orig = reg._scan_root

    def spy(r: Path) -> dict[str, Path]:
        calls["n"] += 1
        return orig(r)

    monkeypatch.setattr(reg, "_scan_root", spy)
    reg.add_root(r2)
    reg.resolve("pkg2")
    assert calls["n"] >= 1
    # remove also invalidates
    calls["n"] = 0
    reg.remove_root(r2)
    reg.resolve("pkg")
    assert calls["n"] >= 1


def test_refresh_clears_cache(
    cfg_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "reg"
    root.mkdir()
    _make_package(root, "p", "pkg", generations=[("0000001", "sha256:z")], current="0000001")
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(root)
    reg.resolve("pkg")
    calls = {"n": 0}
    orig = reg._scan_root

    def spy(r: Path) -> dict[str, Path]:
        calls["n"] += 1
        return orig(r)

    monkeypatch.setattr(reg, "_scan_root", spy)
    reg.refresh()
    reg.resolve("pkg")
    assert calls["n"] == 1


# --- config load edge cases --------------------------------------------------

def test_config_missing_file_empty_roots(cfg_dir: Path) -> None:
    reg = FederatedRegistry(config_dir=cfg_dir)
    assert reg.list_roots() == []


def test_config_empty_file_empty_roots(cfg_dir: Path) -> None:
    (cfg_dir / "federation.yaml").write_text("", encoding="utf-8")
    reg = FederatedRegistry(config_dir=cfg_dir)
    assert reg.list_roots() == []


def test_config_version_mismatch_raises(cfg_dir: Path) -> None:
    (cfg_dir / "federation.yaml").write_text(
        yaml.safe_dump({"version": 99, "roots": []}), encoding="utf-8"
    )
    with pytest.raises(FederationConfigError):
        FederatedRegistry(config_dir=cfg_dir)


def test_config_roots_not_list_raises(cfg_dir: Path) -> None:
    (cfg_dir / "federation.yaml").write_text(
        yaml.safe_dump({"version": 1, "roots": {"a": "b"}}), encoding="utf-8"
    )
    with pytest.raises(FederationConfigError):
        FederatedRegistry(config_dir=cfg_dir)


def test_persistence_preserves_order(cfg_dir: Path, tmp_path: Path) -> None:
    a = tmp_path / "z-alpha"
    a.mkdir()
    b = tmp_path / "a-beta"
    b.mkdir()
    reg = FederatedRegistry(config_dir=cfg_dir)
    reg.add_root(a)
    reg.add_root(b)
    reg2 = FederatedRegistry(config_dir=cfg_dir)
    assert reg2.list_roots() == [a.resolve(), b.resolve()]


def test_exception_hierarchy() -> None:
    for cls in (
        PackageNotFoundInFederationError,
        RevisionNotFoundError,
        AmbiguousPackageError,
        FederationConfigError,
    ):
        assert issubclass(cls, FederationError)
    assert issubclass(FederationError, Exception)
