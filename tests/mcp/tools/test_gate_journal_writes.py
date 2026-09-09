"""Phase 2 Task 18 — architect_gate appends to .architecture/gates.jsonl.

Verifies the fail-soft journal wiring on top of the existing gate tool:
- After a successful gate run, exactly one JSONL line appears in the
  repository's ``.architecture/gates.jsonl`` file.
- The line has the expected shape (gate_id, outcome, findings,
  timestamp) and the outcome matches ``phase_requirements_met``.
- Journal errors NEVER propagate to the caller (fail-soft).
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
import yaml

from opencode_arch.mcp.tools.gate import check_gate


_MODEL_YAML = """\
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


def _write_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "alpha.py").write_text("def go():\n    return 1\n")
    (repo / ".architecture-model.yaml").write_text(_MODEL_YAML)
    return repo


def test_architect_gate_appends_gates_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("AMS_DETERMINISTIC_NOW", "2026-01-01T00:00:00Z")
    repo = _write_repo(tmp_path)
    result = asyncio.run(check_gate(str(repo)))
    assert "error" not in result, result

    journal = repo / ".architecture" / "gates.jsonl"
    assert journal.exists(), "gates.jsonl was not written"
    lines = [ln for ln in journal.read_text().splitlines() if ln.strip()]
    assert len(lines) == 1, f"expected exactly one line, got {lines!r}"

    record = json.loads(lines[0])
    assert record["gate_id"] == "architect_gate"
    assert record["outcome"] in ("pass", "fail")
    # outcome must reflect phase_requirements_met (bool → pass/fail).
    expected = "pass" if result.get("phase_requirements_met") else "fail"
    assert record["outcome"] == expected
    assert record["timestamp"] == "2026-01-01T00:00:00Z"
    assert isinstance(record["findings"], list)


def test_multiple_gate_calls_produce_multiple_lines(tmp_path, monkeypatch):
    monkeypatch.setenv("AMS_DETERMINISTIC_NOW", "2026-02-02T02:02:02Z")
    repo = _write_repo(tmp_path)
    for _ in range(3):
        result = asyncio.run(check_gate(str(repo)))
        assert "error" not in result
    lines = [
        ln for ln in (repo / ".architecture" / "gates.jsonl").read_text().splitlines()
        if ln.strip()
    ]
    assert len(lines) == 3


def test_journal_write_failure_does_not_break_gate(tmp_path, monkeypatch):
    """Simulate a journal-write failure — gate result must still return normally."""
    repo = _write_repo(tmp_path)

    def _boom(*a, **kw):
        raise OSError("simulated disk full")

    # Patch the append import used inside gate.py.
    import architecture_model.feedback.gates as gates_mod
    monkeypatch.setattr(gates_mod, "append", _boom)

    result = asyncio.run(check_gate(str(repo)))
    # Fail-soft: gate should still return a well-formed result.
    assert "error" not in result
    assert "phase_requirements_met" in result
    # No journal file should have been created.
    assert not (repo / ".architecture" / "gates.jsonl").exists()
