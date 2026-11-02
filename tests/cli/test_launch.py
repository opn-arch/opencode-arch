"""Tests for the `opencode-arch` launch path (bare invocation + `launch`)."""
from __future__ import annotations

from unittest.mock import patch

import pytest


class TestRunLaunch:
    def test_skip_exec_returns_repo_and_binary(self, tmp_path):
        from opencode_arch.cli.launch import run_launch

        with patch("shutil.which", return_value="/fake/bin/opencode"):
            result = run_launch(repo_path=str(tmp_path), skip_exec=True)

        assert result["repo"] == str(tmp_path.resolve())
        assert result["opencode"] == "/fake/bin/opencode"

    def test_defaults_to_current_directory(self, tmp_path, monkeypatch):
        from opencode_arch.cli.launch import run_launch

        monkeypatch.chdir(tmp_path)
        with patch("shutil.which", return_value="/fake/bin/opencode"):
            result = run_launch(skip_exec=True)

        assert result["repo"] == str(tmp_path.resolve())

    def test_missing_opencode_binary_exits(self, tmp_path):
        from opencode_arch.cli.launch import run_launch

        with patch("shutil.which", return_value=None):
            with pytest.raises(SystemExit):
                run_launch(repo_path=str(tmp_path), skip_exec=True)

    def test_invalid_directory_exits(self, tmp_path):
        from opencode_arch.cli.launch import run_launch

        missing = tmp_path / "does-not-exist"
        with patch("shutil.which", return_value="/fake/bin/opencode"):
            with pytest.raises(SystemExit):
                run_launch(repo_path=str(missing), skip_exec=True)


class TestMainDispatch:
    def test_bare_invocation_launches_cwd(self):
        from opencode_arch.cli import main as main_mod

        with patch("opencode_arch.cli.launch.run_launch") as rl:
            with patch("sys.argv", ["opencode-arch"]):
                main_mod.main()
        rl.assert_called_once_with(repo_path=None)

    def test_path_argument_launches_that_repo(self, tmp_path):
        from opencode_arch.cli import main as main_mod

        with patch("opencode_arch.cli.launch.run_launch") as rl:
            with patch("sys.argv", ["opencode-arch", str(tmp_path)]):
                main_mod.main()
        rl.assert_called_once_with(repo_path=str(tmp_path))

    def test_launch_subcommand_with_path(self, tmp_path):
        from opencode_arch.cli import main as main_mod

        with patch("opencode_arch.cli.launch.run_launch") as rl:
            with patch("sys.argv", ["opencode-arch", "launch", str(tmp_path)]):
                main_mod.main()
        rl.assert_called_once_with(repo_path=str(tmp_path))

    def test_launch_subcommand_without_path(self):
        from opencode_arch.cli import main as main_mod

        with patch("opencode_arch.cli.launch.run_launch") as rl:
            with patch("sys.argv", ["opencode-arch", "launch"]):
                main_mod.main()
        rl.assert_called_once_with(repo_path=None)

    def test_known_subcommand_does_not_launch(self):
        from opencode_arch.cli import main as main_mod

        with patch("opencode_arch.cli.launch.run_launch") as rl:
            with patch("opencode_arch.cli.metrics.show_metrics") as sm:
                with patch("sys.argv", ["opencode-arch", "metrics"]):
                    main_mod.main()
        rl.assert_not_called()
        sm.assert_called_once()
