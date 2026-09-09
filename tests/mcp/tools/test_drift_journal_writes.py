"""Phase 2 Task 19 — post-pipeline hook appends to .architecture/drift.jsonl.

Exercises ``_append_drift_snapshot`` directly (unit-level; the full
``run_pipeline`` invocation is exercised elsewhere and would be slow
here). Verifies:

* One well-formed JSONL line per call.
* Correct drift kinds: ``orphan``, ``unrealized_capability``,
  ``broken_ref``, ``missing_impl``.
* Clean model → snapshot with empty flags.
* Missing model file → silent no-op.
"""
from __future__ import annotations

import json
from pathlib import Path

from opencode_arch.mcp.tools.pipeline import _append_drift_snapshot


_CLEAN = """\
meta:
  schema_version: '2.1'
  project: t
entities:
  components:
    - id: COMP-1
      name: Alpha
      status: ACTIVE
      files: [alpha.py]
  capabilities:
    - id: CAP-1
      name: Serve
      status: ACTIVE
relationships:
  - from: COMP-1
    to: CAP-1
    type: realizes
"""

_DRIFTY = """\
meta:
  schema_version: '2.1'
  project: t
entities:
  components:
    - id: COMP-1
      name: Alpha
      status: ACTIVE
      files: [alpha.py]
    - id: COMP-2
      name: Beta            # orphan (no relationships) + missing_impl
      status: ACTIVE
    - id: COMP-3
      name: Gamma           # missing_impl (no files) but referenced
      status: ACTIVE
  capabilities:
    - id: CAP-1
      name: Serve           # realized
      status: ACTIVE
    - id: CAP-2
      name: Orphaned        # unrealized_capability
      status: ACTIVE
relationships:
  - from: COMP-1
    to: CAP-1
    type: realizes
  - from: COMP-3
    to: CAP-NONE            # broken_ref
    type: realizes
"""


def _write_model(tmp_path: Path, yaml_text: str) -> Path:
    (tmp_path / ".architecture-model.yaml").write_text(yaml_text)
    return tmp_path


def test_no_model_file_is_silent_noop(tmp_path):
    # No .architecture-model.yaml → returns without writing anything.
    _append_drift_snapshot(tmp_path)
    assert not (tmp_path / ".architecture" / "drift.jsonl").exists()


def test_clean_model_produces_empty_flags_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("AMS_DETERMINISTIC_NOW", "2026-01-01T00:00:00Z")
    _write_model(tmp_path, _CLEAN)
    _append_drift_snapshot(tmp_path)
    journal = tmp_path / ".architecture" / "drift.jsonl"
    lines = [ln for ln in journal.read_text().splitlines() if ln.strip()]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["flags"] == []
    assert rec["timestamp"] == "2026-01-01T00:00:00Z"
    assert rec["model_revision"]  # non-empty (schema_version fallback)


def test_drifty_model_flags_all_kinds(tmp_path):
    _write_model(tmp_path, _DRIFTY)
    _append_drift_snapshot(tmp_path)
    lines = [
        ln
        for ln in (tmp_path / ".architecture" / "drift.jsonl").read_text().splitlines()
        if ln.strip()
    ]
    assert len(lines) == 1
    flags = json.loads(lines[0])["flags"]
    kinds_by_entity = {(f["entity_id"], f["kind"]) for f in flags}

    # broken_ref: relationship endpoint CAP-NONE does not exist.
    assert ("CAP-NONE", "broken_ref") in kinds_by_entity
    # unrealized_capability: CAP-2 has no realizing relationship.
    assert ("CAP-2", "unrealized_capability") in kinds_by_entity
    # orphan: COMP-2 is in no relationship.
    assert ("COMP-2", "orphan") in kinds_by_entity
    # missing_impl: COMP-2 has no files.
    assert ("COMP-2", "missing_impl") in kinds_by_entity
    # missing_impl: COMP-3 has no files (though it is referenced).
    assert ("COMP-3", "missing_impl") in kinds_by_entity


def test_repeated_calls_append_lines(tmp_path):
    _write_model(tmp_path, _CLEAN)
    _append_drift_snapshot(tmp_path)
    _append_drift_snapshot(tmp_path)
    _append_drift_snapshot(tmp_path)
    lines = [
        ln
        for ln in (tmp_path / ".architecture" / "drift.jsonl").read_text().splitlines()
        if ln.strip()
    ]
    assert len(lines) == 3
