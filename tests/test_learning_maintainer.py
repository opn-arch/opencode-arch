"""Tests for documentation drift detection and auto-fix."""
import json
from pathlib import Path

import pytest

from opencode_arch.learning.maintainer import (
    detect_drift,
    auto_fix_drift,
    _check_version_sync,
    _check_python_version,
    DriftFlag,
)


class TestVersionSync:
    def test_detects_version_mismatch(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('version = "1.2.0"\n')
        src = tmp_path / "src" / "pkg"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text('__version__ = "1.0.0"\n')

        flag = _check_version_sync(tmp_path)
        assert flag is not None
        assert "1.0.0" in flag.issue
        assert "1.2.0" in flag.issue
        assert flag.auto_fixable

    def test_no_flag_when_versions_match(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('version = "1.2.0"\n')
        src = tmp_path / "src" / "pkg"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text('__version__ = "1.2.0"\n')

        flag = _check_version_sync(tmp_path)
        assert flag is None


class TestPythonVersion:
    def test_detects_readme_mismatch(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('requires-python = ">=3.11"\n')
        (tmp_path / "README.md").write_text("Requires Python 3.10+\n")

        flag = _check_python_version(tmp_path)
        assert flag is not None
        assert "3.10" in flag.issue
        assert "3.11" in flag.issue

    def test_no_flag_when_matches(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('requires-python = ">=3.11"\n')
        (tmp_path / "README.md").write_text("Requires Python 3.11+\n")

        flag = _check_python_version(tmp_path)
        assert flag is None


class TestAutoFix:
    def test_fixes_version_mismatch(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('version = "2.0.0"\n')
        init = tmp_path / "myfile.py"
        init.write_text('__version__ = "1.0.0"\n')

        flag = DriftFlag(
            file="myfile.py",
            issue="__version__='1.0.0' != pyproject.toml version='2.0.0'",
            severity="high",
            auto_fixable=True,
            suggested_fix="Update __version__ to '2.0.0'",
        )

        fixed = auto_fix_drift([flag], tmp_path)
        assert len(fixed) == 1
        assert '2.0.0' in init.read_text()

    def test_fixes_python_version(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("Requires Python 3.10+ to run.\n")

        flag = DriftFlag(
            file="README.md",
            issue="README says Python 3.10+ but pyproject requires >=3.11",
            severity="medium",
            auto_fixable=True,
            suggested_fix="Replace 'Python 3.10+' with 'Python 3.11+'",
        )

        fixed = auto_fix_drift([flag], tmp_path)
        assert len(fixed) == 1
        assert "3.11+" in readme.read_text()

    def test_skips_non_fixable(self, tmp_path):
        flag = DriftFlag(
            file="schema.json",
            issue="Version mismatch",
            severity="high",
            auto_fixable=False,
        )

        fixed = auto_fix_drift([flag], tmp_path)
        assert len(fixed) == 0


class TestDetectDrift:
    def test_detects_multiple_issues(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nversion = "2.0.0"\nrequires-python = ">=3.12"\n'
        )
        src = tmp_path / "src" / "pkg"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text('__version__ = "1.0.0"\n')
        (tmp_path / "README.md").write_text("402 tests passing. Python 3.10+\n")

        flags = detect_drift(tmp_path)
        # Should find at least version mismatch and python version
        assert len(flags) >= 2

    def test_clean_project_no_flags(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nversion = "1.0.0"\nrequires-python = ">=3.11"\n'
        )
        src = tmp_path / "src" / "pkg"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text('__version__ = "1.0.0"\n')
        (tmp_path / "README.md").write_text("Needs Python 3.11+\n")

        flags = detect_drift(tmp_path)
        # Should find no version or python issues (test count check won't run without pytest)
        version_flags = [f for f in flags if "version" in f.issue.lower() or "Python" in f.issue]
        assert len(version_flags) == 0
