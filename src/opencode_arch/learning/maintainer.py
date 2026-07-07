"""Documentation drift detection and auto-fix.

Checks for discrepancies between code reality and documentation,
then either flags issues or auto-fixes simple cases.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DriftFlag:
    """A detected documentation drift issue."""
    file: str                    # which doc is out of date
    issue: str                   # what's wrong
    severity: str                # "blocker", "high", "medium", "low"
    auto_fixable: bool = False   # can we fix it programmatically?
    suggested_fix: str = ""      # what to change
    fixed: bool = False          # was it auto-fixed?


def _check_test_count(project_root: Path) -> DriftFlag | None:
    """Check if README test count matches actual."""
    readme = project_root / "README.md"
    if not readme.exists():
        return None
    
    content = readme.read_text(encoding="utf-8")
    
    # Find test count claims in README
    match = re.search(r"(\d+)\s+tests?\s+pass", content, re.IGNORECASE)
    if not match:
        return None
    
    claimed_count = int(match.group(1))
    
    # Run actual test count (collect only, don't execute)
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q",
             "--ignore=tests/test_config_loader.py"],
            capture_output=True, text=True, cwd=str(project_root), timeout=30,
        )
        # Parse "X tests collected" or "X items"
        count_match = re.search(r"(\d+) tests? (?:collected|selected)", result.stdout)
        if not count_match:
            # Try alternate format
            count_match = re.search(r"(\d+) items?", result.stdout)
        if not count_match:
            return None
        
        actual_count = int(count_match.group(1))
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    
    if abs(actual_count - claimed_count) > 5:  # Allow small variance
        return DriftFlag(
            file=str(readme.relative_to(project_root)),
            issue=f"README claims {claimed_count} tests but actual is {actual_count}",
            severity="medium",
            auto_fixable=True,
            suggested_fix=f"Replace '{claimed_count}' with '{actual_count}' in test count",
        )
    return None


def _check_version_sync(project_root: Path) -> DriftFlag | None:
    """Check if version in pyproject.toml matches __init__.py."""
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        return None
    
    pyproject_content = pyproject.read_text(encoding="utf-8")
    version_match = re.search(r'version\s*=\s*"([^"]+)"', pyproject_content)
    if not version_match:
        return None
    pyproject_version = version_match.group(1)
    
    # Find __init__.py
    for init_path in project_root.rglob("__init__.py"):
        rel = str(init_path.relative_to(project_root))
        if "test" in rel or ".venv" in rel:
            continue
        try:
            init_content = init_path.read_text(encoding="utf-8")
            init_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', init_content)
            if init_match:
                init_version = init_match.group(1)
                if init_version != pyproject_version:
                    rel_path = init_path.relative_to(project_root)
                    return DriftFlag(
                        file=str(rel_path),
                        issue=f"__version__='{init_version}' != pyproject.toml version='{pyproject_version}'",
                        severity="high",
                        auto_fixable=True,
                        suggested_fix=f"Update __version__ to '{pyproject_version}'",
                    )
                break  # Found and matches
        except (UnicodeDecodeError, OSError):
            continue
    return None


def _check_schema_version(project_root: Path) -> DriftFlag | None:
    """Check if schema.json version matches CONTEXT.md claims."""
    schema_path = project_root / "src" / "architecture_model" / "spec" / "schema.json"
    context_path = project_root / "CONTEXT.md"
    
    if not schema_path.exists() or not context_path.exists():
        return None
    
    try:
        import json
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema_id = schema.get("$id", "")
        # Extract version from $id URL
        schema_version_match = re.search(r"v?([\d.]+)", schema_id)
        if not schema_version_match:
            return None
        schema_version = schema_version_match.group(1)
        
        context_content = context_path.read_text(encoding="utf-8")
        context_match = re.search(r"[Ss]chema version:?\s*([\d.]+)", context_content)
        if not context_match:
            return None
        context_version = context_match.group(1)
        
        if schema_version != context_version:
            return DriftFlag(
                file="src/architecture_model/spec/schema.json",
                issue=f"Schema $id version ({schema_version}) != CONTEXT.md ({context_version})",
                severity="medium",
                auto_fixable=False,
                suggested_fix=f"Align schema $id version to {context_version}",
            )
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _check_python_version(project_root: Path) -> DriftFlag | None:
    """Check if README Python version matches pyproject.toml requires-python."""
    readme = project_root / "README.md"
    pyproject = project_root / "pyproject.toml"
    
    if not readme.exists() or not pyproject.exists():
        return None
    
    pyproject_content = pyproject.read_text(encoding="utf-8")
    req_match = re.search(r'requires-python\s*=\s*"([^"]+)"', pyproject_content)
    if not req_match:
        return None
    
    # Extract minimum version from requires-python (e.g., ">=3.11" -> "3.11")
    min_version_match = re.search(r"(\d+\.\d+)", req_match.group(1))
    if not min_version_match:
        return None
    min_version = min_version_match.group(1)
    
    readme_content = readme.read_text(encoding="utf-8")
    readme_match = re.search(r"Python\s+(\d+\.\d+)\+?", readme_content)
    if not readme_match:
        return None
    
    readme_version = readme_match.group(1)
    if readme_version != min_version:
        return DriftFlag(
            file="README.md",
            issue=f"README says Python {readme_version}+ but pyproject requires >={min_version}",
            severity="medium",
            auto_fixable=True,
            suggested_fix=f"Replace 'Python {readme_version}+' with 'Python {min_version}+'",
        )
    return None


def detect_drift(project_root: Path) -> list[DriftFlag]:
    """Run all drift detection checks on a project.
    
    Args:
        project_root: Path to the project to check.
    
    Returns:
        List of detected drift issues (may be empty if all is well).
    """
    checks = [
        _check_test_count,
        _check_version_sync,
        _check_schema_version,
        _check_python_version,
    ]
    
    flags: list[DriftFlag] = []
    for check in checks:
        try:
            flag = check(project_root)
            if flag:
                flags.append(flag)
        except Exception:
            pass  # Drift detection is best-effort
    
    return flags


def auto_fix_drift(flags: list[DriftFlag], project_root: Path) -> list[DriftFlag]:
    """Auto-fix drift flags that are marked as auto_fixable.
    
    Args:
        flags: List of detected drift flags.
        project_root: Path to the project root.
    
    Returns:
        List of flags that were successfully fixed.
    """
    fixed: list[DriftFlag] = []
    
    for flag in flags:
        if not flag.auto_fixable:
            continue
        
        file_path = project_root / flag.file
        if not file_path.exists():
            continue
        
        try:
            content = file_path.read_text(encoding="utf-8")
            new_content = content
            
            if "test count" in flag.issue.lower() or "tests" in flag.issue.lower():
                # Fix test count
                match = re.search(r"(\d+)\s+tests?\s+pass", flag.issue)
                new_match = re.search(r"actual is (\d+)", flag.issue)
                if match and new_match:
                    old_count = match.group(1)
                    new_count = new_match.group(1)
                    new_content = re.sub(
                        rf"{old_count}(\s+tests?\s+pass)",
                        f"{new_count}\\1",
                        content,
                    )
            
            elif "__version__" in flag.issue:
                # Fix version mismatch
                match = re.search(r"to '([^']+)'", flag.suggested_fix)
                if match:
                    target_version = match.group(1)
                    new_content = re.sub(
                        r'__version__\s*=\s*["\'][^"\']+["\']',
                        f'__version__ = "{target_version}"',
                        content,
                    )
            
            elif "Python" in flag.issue:
                # Fix Python version
                match = re.search(r"Python ([\d.]+)\+.*Python ([\d.]+)\+", flag.suggested_fix)
                if match:
                    old_ver = match.group(1)
                    new_ver = match.group(2)
                    new_content = content.replace(f"Python {old_ver}+", f"Python {new_ver}+")
                else:
                    # Try alternate parsing from issue text
                    old_match = re.search(r"says Python ([\d.]+)", flag.issue)
                    new_match_ver = re.search(r"requires >=([\d.]+)", flag.issue)
                    if old_match and new_match_ver:
                        old_ver = old_match.group(1)
                        new_ver = new_match_ver.group(1)
                        new_content = content.replace(f"Python {old_ver}+", f"Python {new_ver}+")
            
            if new_content != content:
                file_path.write_text(new_content, encoding="utf-8")
                flag.fixed = True
                fixed.append(flag)
        
        except (OSError, UnicodeDecodeError):
            pass
    
    return fixed
