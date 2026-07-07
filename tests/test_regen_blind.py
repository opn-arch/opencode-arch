"""Tests for blind mode in regen-loop."""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import dataclass, field

from opencode_arch.cli.regen_loop import _setup_blind_workdir, run_regen_loop
from opencode_arch.runner.base import RunResult


@dataclass
class _FakeSubsystem:
    name: str
    source_files: list = field(default_factory=list)
    test_files: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)


class TestSetupBlindWorkdir:
    """Test the blind mode working directory setup."""

    def test_copies_test_files(self, tmp_path):
        """Test files should be copied, source files should NOT."""
        pkg = tmp_path / "mypackage"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "module.py").write_text("def foo(): return 1")
        tests = pkg / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("")
        (tests / "test_module.py").write_text("def test_foo(): pass")

        test_files = [tests / "test_module.py"]
        work_dir = _setup_blind_workdir(tmp_path, test_files)

        # Test files should be copied
        assert (work_dir / "mypackage" / "tests" / "test_module.py").exists()
        # Source files should NOT be copied
        assert not (work_dir / "mypackage" / "module.py").exists()
        # Package init should be created for imports to work
        assert (work_dir / "mypackage" / "__init__.py").exists()

    def test_preserves_directory_structure(self, tmp_path):
        """Directory hierarchy for test imports must be maintained."""
        pkg = tmp_path / "colorama"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        tests = pkg / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("")
        (tests / "ansi_test.py").write_text("import colorama.ansi")

        test_files = [tests / "ansi_test.py"]
        work_dir = _setup_blind_workdir(tmp_path, test_files)

        # Directory structure preserved
        assert (work_dir / "colorama").is_dir()
        assert (work_dir / "colorama" / "tests").is_dir()
        assert (work_dir / "colorama" / "tests" / "ansi_test.py").exists()

    def test_copies_conftest(self, tmp_path):
        """conftest.py files should be copied for pytest fixtures."""
        pkg = tmp_path / "mylib"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        tests = pkg / "tests"
        tests.mkdir()
        (tests / "conftest.py").write_text("import pytest\n@pytest.fixture\ndef x(): return 1")
        (tests / "test_a.py").write_text("def test_a(x): assert x == 1")

        test_files = [tests / "test_a.py"]
        work_dir = _setup_blind_workdir(tmp_path, test_files)

        # conftest should be copied alongside test files
        assert (work_dir / "mylib" / "tests" / "conftest.py").exists()

    def test_copies_root_conftest(self, tmp_path):
        """Root-level conftest.py should also be copied."""
        (tmp_path / "conftest.py").write_text("import pytest")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_x.py").write_text("def test_x(): pass")

        test_files = [tests / "test_x.py"]
        work_dir = _setup_blind_workdir(tmp_path, test_files)

        assert (work_dir / "conftest.py").exists()

    def test_copies_pyproject_toml(self, tmp_path):
        """pyproject.toml should be copied for import resolution."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'mylib'\n")
        pkg = tmp_path / "src" / "mylib"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_a.py").write_text("def test_a(): pass")

        test_files = [tests / "test_a.py"]
        work_dir = _setup_blind_workdir(tmp_path, test_files)

        assert (work_dir / "pyproject.toml").exists()

    def test_copies_setup_py(self, tmp_path):
        """setup.py should be copied if it exists."""
        (tmp_path / "setup.py").write_text("from setuptools import setup; setup()")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_z.py").write_text("def test_z(): pass")

        test_files = [tests / "test_z.py"]
        work_dir = _setup_blind_workdir(tmp_path, test_files)

        assert (work_dir / "setup.py").exists()

    def test_creates_empty_init_for_parent_packages(self, tmp_path):
        """Parent packages get empty __init__.py for import resolution."""
        deep = tmp_path / "pkg" / "sub" / "deep"
        deep.mkdir(parents=True)
        (tmp_path / "pkg" / "__init__.py").write_text("VERSION = '1.0'")
        (tmp_path / "pkg" / "sub" / "__init__.py").write_text("")
        (tmp_path / "pkg" / "sub" / "deep" / "__init__.py").write_text("")
        (tmp_path / "pkg" / "sub" / "deep" / "test_inner.py").write_text("def test_inner(): pass")

        test_files = [deep / "test_inner.py"]
        work_dir = _setup_blind_workdir(tmp_path, test_files)

        # All parent __init__.py should exist (empty - no source content)
        assert (work_dir / "pkg" / "__init__.py").exists()
        assert (work_dir / "pkg" / "sub" / "__init__.py").exists()
        assert (work_dir / "pkg" / "sub" / "deep" / "__init__.py").exists()


class TestRunRegenLoopBlind:
    """Test that blind=True routes through the blind workdir."""

    @pytest.mark.asyncio
    async def test_blind_uses_temp_workdir(self):
        """In blind mode, runner.run() should receive a temp dir, not repo_path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            test_file = tmpdir / "test_core.py"
            test_file.write_text("def test_ok():\n    assert True\n")
            source_file = tmpdir / "core.py"
            source_file.write_text("x = 1\n")

            subsystem = _FakeSubsystem(
                name="core",
                source_files=[source_file],
                test_files=[test_file],
                dependencies=[],
            )

            mock_runner = AsyncMock()
            mock_runner.run.return_value = RunResult(output="done", exit_code=0, success=True)

            with patch("opencode_arch.cli.regen_loop.test_affinity_decompose", return_value=[subsystem]), \
                 patch("opencode_arch.cli.regen_loop.analyze_test_file") as mock_analyze, \
                 patch("opencode_arch.cli.regen_loop._record_outcome"):
                mock_analyze.return_value = MagicMock(contracts=[], constants=[], required_imports=[])

                result = await run_regen_loop(
                    repo_path=tmpdir,
                    runner=mock_runner,
                    target_pass_rate=0.5,
                    blind=True,
                )

                # Runner should have been called with a different path (temp dir)
                call_args = mock_runner.run.call_args
                repo_path_used = call_args.kwargs.get("repo_path") or call_args[1].get("repo_path") or call_args[0][1] if len(call_args[0]) > 1 else None
                if repo_path_used is None:
                    # Try keyword arg
                    repo_path_used = call_args.kwargs.get("repo_path", "")
                # In blind mode, should NOT be the original repo path
                assert str(tmpdir) != repo_path_used

    @pytest.mark.asyncio
    async def test_blind_mode_passes_signatures(self):
        """In blind mode, signatures should be extracted from model and included in prompt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            test_file = tmpdir / "test_core.py"
            test_file.write_text("def test_ok():\n    assert True\n")

            subsystem = _FakeSubsystem(
                name="core",
                source_files=[Path("src/core.py")],
                test_files=[test_file],
                dependencies=[],
            )

            mock_runner = AsyncMock()
            mock_runner.run.return_value = RunResult(output="done", exit_code=0, success=True)

            # Mock model loading to return signatures
            fake_sig = MagicMock()
            fake_sig.name = "init"
            fake_sig.params = ["self", "config"]
            fake_sig.returns = "None"
            fake_sig.body_hint = "initializes config"

            with patch("opencode_arch.cli.regen_loop.test_affinity_decompose", return_value=[subsystem]), \
                 patch("opencode_arch.cli.regen_loop.analyze_test_file") as mock_analyze, \
                 patch("opencode_arch.cli.regen_loop._record_outcome"), \
                 patch("opencode_arch.cli.regen_loop._extract_signatures_for_subsystem", return_value=[fake_sig]):
                mock_analyze.return_value = MagicMock(contracts=[], constants=[], required_imports=[])

                result = await run_regen_loop(
                    repo_path=tmpdir,
                    runner=mock_runner,
                    target_pass_rate=0.5,
                    blind=True,
                )

                # Verify runner was called (prompt should contain signature info)
                assert mock_runner.run.called
                prompt_used = mock_runner.run.call_args.kwargs.get("prompt") or mock_runner.run.call_args[0][0]
                assert "init(self, config)" in prompt_used
