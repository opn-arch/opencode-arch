"""Repository path resolver for Phase 2 lifecycle executor.

All directory accessors auto-create their target directory (idempotently) and
return an absolute :class:`Path` when given an absolute ``repo_path``. File-path
accessors (index, journal) create only the parent directory.
"""
from __future__ import annotations

from pathlib import Path

LIFECYCLE_ROOT_NAME = ".architecture/lifecycle"
AI_ROOT_NAME = ".architecture/ai"


def _compose_path(repo_path: Path, *parts: str) -> Path:
    """Pure path composition — does not touch disk."""
    root_parts = LIFECYCLE_ROOT_NAME.split("/")
    p = Path(repo_path)
    for part in root_parts:
        p = p / part
    for part in parts:
        p = p / part
    return p


def _compose_ai_path(repo_path: Path, *parts: str) -> Path:
    p = Path(repo_path)
    for part in AI_ROOT_NAME.split("/"):
        p = p / part
    for part in parts:
        p = p / part
    return p


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


# --- lifecycle tree ---------------------------------------------------------

def package_root(repo_path: Path) -> Path:
    return _ensure_dir(_compose_path(repo_path))


def package_index_path(repo_path: Path) -> Path:
    p = _compose_path(repo_path, "index.yaml")
    _ensure_dir(p.parent)
    return p


def slice_dir(repo_path: Path) -> Path:
    return _ensure_dir(_compose_path(repo_path, "slices"))


def view_dir(repo_path: Path) -> Path:
    return _ensure_dir(_compose_path(repo_path, "views"))


def artifact_dir(repo_path: Path) -> Path:
    return _ensure_dir(_compose_path(repo_path, "artifacts"))


def artifact_spec_dir(repo_path: Path) -> Path:
    return _ensure_dir(_compose_path(repo_path, "artifact_specs"))


def journal_path(repo_path: Path) -> Path:
    p = _compose_path(repo_path, "journal.jsonl")
    _ensure_dir(p.parent)
    return p


# --- ai tree ----------------------------------------------------------------

def workorder_dir(repo_path: Path) -> Path:
    return _ensure_dir(_compose_ai_path(repo_path, "workorders"))


def job_dir(repo_path: Path) -> Path:
    return _ensure_dir(_compose_ai_path(repo_path, "jobs"))


def proposal_dir(repo_path: Path) -> Path:
    return _ensure_dir(_compose_ai_path(repo_path, "proposals"))


# --- bulk -------------------------------------------------------------------

def ensure_all(repo_path: Path) -> dict[str, Path]:
    return {
        "package_root": package_root(repo_path),
        "slice_dir": slice_dir(repo_path),
        "view_dir": view_dir(repo_path),
        "artifact_dir": artifact_dir(repo_path),
        "artifact_spec_dir": artifact_spec_dir(repo_path),
        "workorder_dir": workorder_dir(repo_path),
        "job_dir": job_dir(repo_path),
        "proposal_dir": proposal_dir(repo_path),
    }
