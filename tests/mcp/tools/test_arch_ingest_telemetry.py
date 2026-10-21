"""Tests for the arch_ingest_telemetry B-ROUND write MCP tool.

A WRITE tool (counterpart to the pure-read ``arch_observe``) that appends
externally-supplied observation events to the repo's journal
(``<repo_path>/.architecture/observations.jsonl``), validating each event's
shape via the canonical ``Observation`` dataclass and returning an ingest
summary ``{"ingested": <int>, "rejected": <int>}``.

NOTE: arch_ingest_telemetry is itself instrumented (wrapped in
``observe_tool_call``), so each invocation ALSO appends its own
``oca:arch_ingest_telemetry`` ``tool_call`` record to the journal. Tests
therefore use membership/subset assertions against ``journal.read`` (the
self-entry is always present) and assert the returned counts (which count
ONLY the supplied events, never the self-entry).
"""
from __future__ import annotations

import asyncio

from opencode_arch.mcp.tools.arch_ingest_telemetry import arch_ingest_telemetry
from openag.observe import journal


def _run(coro):
    return asyncio.run(coro)


def _valid_event(ts: str | None = None, **overrides):
    ev = {
        "component_id": "COMP-A",
        "io_kind": "tool_call",
        "direction": "in",
        "name": "do",
        "payload_digest": "",
        "meta": {},
    }
    if ts is not None:
        ev["ts"] = ts
    ev.update(overrides)
    return ev


def test_happy_path_ingests_two_valid_events(tmp_path):
    e1 = _valid_event(ts="2026-01-01T00:00:00+00:00", name="first")
    e2 = _valid_event(ts="2026-02-01T00:00:00+00:00", name="second",
                      component_id="COMP-B", io_kind="llm_call", direction="out")
    out = _run(arch_ingest_telemetry(repo_path=str(tmp_path), events=[e1, e2]))
    assert out["ok"] is True
    assert out["ingested"] == 2
    assert out["rejected"] == 0

    records = journal.read(tmp_path)
    # Canonical stored shape: 6 Observation fields + preserved ts.
    assert {
        "component_id": "COMP-A", "io_kind": "tool_call", "direction": "in",
        "name": "first", "payload_digest": "", "meta": {},
        "ts": "2026-01-01T00:00:00+00:00",
    } in records
    assert {
        "component_id": "COMP-B", "io_kind": "llm_call", "direction": "out",
        "name": "second", "payload_digest": "", "meta": {},
        "ts": "2026-02-01T00:00:00+00:00",
    } in records


def test_ts_preserved_when_supplied(tmp_path):
    ts = "2026-01-01T00:00:00+00:00"
    out = _run(arch_ingest_telemetry(repo_path=str(tmp_path),
                                     events=[_valid_event(ts=ts, name="keeps-ts")]))
    assert out["ok"] is True
    assert out["ingested"] == 1
    stored = [r for r in journal.read(tmp_path) if r.get("name") == "keeps-ts"]
    assert len(stored) == 1
    assert stored[0]["ts"] == ts


def test_ts_stamped_when_absent(tmp_path):
    out = _run(arch_ingest_telemetry(repo_path=str(tmp_path),
                                     events=[_valid_event(name="no-ts")]))
    assert out["ok"] is True
    assert out["ingested"] == 1
    stored = [r for r in journal.read(tmp_path) if r.get("name") == "no-ts"]
    assert len(stored) == 1
    assert isinstance(stored[0].get("ts"), str)
    assert stored[0]["ts"] != ""


def test_mixed_valid_and_invalid(tmp_path):
    good = _valid_event(ts="2026-01-01T00:00:00+00:00", name="good")
    bad_non_dict = "not-a-dict"
    bad_missing_name = {
        "component_id": "COMP-A", "io_kind": "tool_call", "direction": "in",
    }
    bad_io_kind = _valid_event(name="bad-io", io_kind="bogus")
    bad_direction = _valid_event(name="bad-dir", direction="sideways")

    out = _run(arch_ingest_telemetry(
        repo_path=str(tmp_path),
        events=[good, bad_non_dict, bad_missing_name, bad_io_kind, bad_direction],
    ))
    assert out["ok"] is True
    assert out["ingested"] == 1
    assert out["rejected"] == 4

    records = journal.read(tmp_path)
    names = [r.get("name") for r in records]
    assert "good" in names
    assert "bad-io" not in names
    assert "bad-dir" not in names
    # Only the good supplied event (plus the tool's own self-entry) landed.
    supplied = [r for r in records
                if r.get("component_id", "").startswith("COMP-")]
    assert len(supplied) == 1


def test_empty_ts_is_stamped(tmp_path):
    # The `isinstance(ts, str) and ts` guard treats ts="" as absent and falls
    # through to stamping — guards that deliberate clause against a refactor
    # to `if "ts" in ev:` that would silently store the empty string.
    out = _run(arch_ingest_telemetry(repo_path=str(tmp_path),
                                     events=[_valid_event(ts="", name="empty-ts")]))
    assert out["ok"] is True
    assert out["ingested"] == 1
    stored = [r for r in journal.read(tmp_path) if r.get("name") == "empty-ts"]
    assert len(stored) == 1
    assert isinstance(stored[0].get("ts"), str)
    assert stored[0]["ts"] != ""


def test_append_failure_counts_as_rejected(tmp_path, monkeypatch):
    # A write failure (fail-soft _append_record returns False) is a per-event
    # rejection, NOT a tool error — the only tool-body branch not otherwise
    # covered.
    import opencode_arch.mcp.tools.arch_ingest_telemetry as mod

    monkeypatch.setattr(mod, "_append_record", lambda repo, record: False)
    out = _run(arch_ingest_telemetry(repo_path=str(tmp_path),
                                     events=[_valid_event(name="x")]))
    assert out["ok"] is True
    assert out["ingested"] == 0
    assert out["rejected"] == 1


def test_empty_list(tmp_path):
    out = _run(arch_ingest_telemetry(repo_path=str(tmp_path), events=[]))
    assert out["ok"] is True
    assert out["ingested"] == 0
    assert out["rejected"] == 0


def test_events_not_a_list_returns_invalid_argument(tmp_path):
    out = _run(arch_ingest_telemetry(str(tmp_path), "nope"))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_missing_repo_returns_not_found():
    out = _run(arch_ingest_telemetry(repo_path="/nonexistent/repo/path",
                                     events=[]))
    assert out["ok"] is False
    assert out["error"]["code"] == "NOT_FOUND"
