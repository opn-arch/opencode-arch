"""Tests for blind workdir test infrastructure copying."""
from pathlib import Path

import pytest


def test_blind_workdir_copies_test_init_files(tmp_path):
    """Blind workdir should copy tests/__init__.py for package imports."""
    from opencode_arch.cli.regen_loop import _setup_blind_workdir

    # Create a repo with test __init__.py
    repo = tmp_path / "repo"
    repo.mkdir()
    tests_dir = repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("# test package init\n")
    (tests_dir / "test_foo.py").write_text("def test_x(): pass\n")
    (tests_dir / "conftest.py").write_text("import pytest\n")
    (repo / "pyproject.toml").write_text("[project]\nname='test'\n")

    test_files = [tests_dir / "test_foo.py"]
    workdir = _setup_blind_workdir(repo, test_files)

    # Should have __init__.py copied with actual content
    init_file = workdir / "tests" / "__init__.py"
    assert init_file.exists()
    assert init_file.read_text() == "# test package init\n"
    assert (workdir / "tests" / "conftest.py").exists()


def test_blind_workdir_copies_helper_modules(tmp_path):
    """Blind workdir should copy non-test .py files from test dirs (helpers)."""
    from opencode_arch.cli.regen_loop import _setup_blind_workdir

    repo = tmp_path / "repo"
    repo.mkdir()
    tests_dir = repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("")
    (tests_dir / "helpers.py").write_text("def make_fixture(): return {}\n")
    (tests_dir / "conftest.py").write_text("from .helpers import make_fixture\n")
    (tests_dir / "test_main.py").write_text(
        "from tests.helpers import make_fixture\ndef test_it(): pass\n"
    )
    (repo / "pyproject.toml").write_text("[project]\nname='test'\n")

    test_files = [tests_dir / "test_main.py"]
    workdir = _setup_blind_workdir(repo, test_files)

    # Helper should be copied
    assert (workdir / "tests" / "helpers.py").exists()
    assert (workdir / "tests" / "helpers.py").read_text() == "def make_fixture(): return {}\n"
    assert (workdir / "tests" / "__init__.py").exists()


def test_blind_workdir_copies_nested_conftest(tmp_path):
    """Blind workdir should copy conftest.py at all levels of test dir tree."""
    from opencode_arch.cli.regen_loop import _setup_blind_workdir

    repo = tmp_path / "repo"
    repo.mkdir()
    tests_dir = repo / "tests"
    sub_dir = tests_dir / "unit"
    sub_dir.mkdir(parents=True)
    (tests_dir / "__init__.py").write_text("")
    (tests_dir / "conftest.py").write_text("# root conftest\n")
    (sub_dir / "__init__.py").write_text("")
    (sub_dir / "conftest.py").write_text("# unit conftest\n")
    (sub_dir / "test_thing.py").write_text("def test_it(): pass\n")
    (repo / "pyproject.toml").write_text("[project]\nname='test'\n")

    test_files = [sub_dir / "test_thing.py"]
    workdir = _setup_blind_workdir(repo, test_files)

    # Both conftest files should exist
    assert (workdir / "tests" / "conftest.py").exists()
    assert (workdir / "tests" / "unit" / "conftest.py").exists()
    assert (workdir / "tests" / "unit" / "__init__.py").exists()


def test_blind_workdir_does_not_copy_other_test_files(tmp_path):
    """Blind workdir should NOT copy other subsystems' test files."""
    from opencode_arch.cli.regen_loop import _setup_blind_workdir

    repo = tmp_path / "repo"
    repo.mkdir()
    tests_dir = repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("")
    (tests_dir / "test_foo.py").write_text("def test_foo(): pass\n")
    (tests_dir / "test_bar.py").write_text("def test_bar(): pass\n")
    (tests_dir / "helpers.py").write_text("SHARED = True\n")
    (repo / "pyproject.toml").write_text("[project]\nname='test'\n")

    # Only include test_foo.py as the subsystem's test
    test_files = [tests_dir / "test_foo.py"]
    workdir = _setup_blind_workdir(repo, test_files)

    # test_foo.py should be there (subsystem test)
    assert (workdir / "tests" / "test_foo.py").exists()
    # test_bar.py should NOT be there (other subsystem)
    assert not (workdir / "tests" / "test_bar.py").exists()
    # helpers.py SHOULD be there (shared infrastructure)
    assert (workdir / "tests" / "helpers.py").exists()
