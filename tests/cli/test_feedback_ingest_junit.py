"""Phase 2 Task 20 — ``opencode-arch feedback ingest-junit`` CLI.

End-to-end test invoking the CLI via ``argparse`` to exercise the full
registration + dispatch path. Verifies:

* Successful ingest writes exactly one line to
  ``<repo>/.architecture/test_results.jsonl``.
* The stdout JSON summary matches the ingested totals.
* Missing JUnit file yields a non-zero exit and no journal write.
* Missing repo-path yields a non-zero exit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from opencode_arch.cli.feedback import (
    dispatch_feedback,
    register_feedback_subparsers,
)


JUNIT_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuite name="mysuite" tests="3" failures="1" skipped="1" errors="0" time="0.42">
  <testcase classname="foo" name="test_a" time="0.1"/>
  <testcase classname="foo" name="test_b" time="0.2">
    <failure message="oops">stack</failure>
  </testcase>
  <testcase classname="foo" name="test_c" time="0.12">
    <skipped/>
  </testcase>
</testsuite>
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opencode-arch")
    sub = parser.add_subparsers(dest="command", required=True)
    register_feedback_subparsers(sub)
    return parser


def test_ingest_junit_writes_journal_and_prints_summary(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("AMS_DETERMINISTIC_NOW", "2026-01-01T00:00:00Z")
    xml = tmp_path / "junit.xml"
    xml.write_text(JUNIT_XML)

    parser = _build_parser()
    args = parser.parse_args(
        ["feedback", "ingest-junit", str(xml), "--repo-path", str(tmp_path)]
    )
    rc = dispatch_feedback(args)
    assert rc == 0

    out = capsys.readouterr().out.strip().splitlines()[-1]
    summary = json.loads(out)
    assert summary["ok"] is True
    assert summary["total"] == 3
    assert summary["failed"] == 1
    assert summary["skipped"] == 1
    assert summary["passed"] == 1
    assert summary["failure_count"] == 1

    journal = tmp_path / ".architecture" / "test_results.jsonl"
    lines = [ln for ln in journal.read_text().splitlines() if ln.strip()]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["suite"] == "mysuite"
    assert rec["total"] == 3
    assert rec["failed"] == 1


def test_ingest_junit_suite_override(tmp_path):
    xml = tmp_path / "junit.xml"
    xml.write_text(JUNIT_XML)

    parser = _build_parser()
    args = parser.parse_args(
        [
            "feedback", "ingest-junit", str(xml),
            "--repo-path", str(tmp_path),
            "--suite", "override-name",
        ]
    )
    rc = dispatch_feedback(args)
    assert rc == 0
    rec = json.loads(
        (tmp_path / ".architecture" / "test_results.jsonl").read_text().splitlines()[0]
    )
    assert rec["suite"] == "override-name"


def test_missing_junit_file_returns_nonzero(tmp_path, capsys):
    parser = _build_parser()
    args = parser.parse_args(
        [
            "feedback", "ingest-junit", str(tmp_path / "nope.xml"),
            "--repo-path", str(tmp_path),
        ]
    )
    rc = dispatch_feedback(args)
    assert rc == 1
    assert "not found" in capsys.readouterr().out.lower()
    assert not (tmp_path / ".architecture" / "test_results.jsonl").exists()


def test_missing_repo_path_returns_nonzero(tmp_path, capsys):
    xml = tmp_path / "junit.xml"
    xml.write_text(JUNIT_XML)
    parser = _build_parser()
    args = parser.parse_args(
        [
            "feedback", "ingest-junit", str(xml),
            "--repo-path", str(tmp_path / "does-not-exist"),
        ]
    )
    rc = dispatch_feedback(args)
    assert rc == 1
    assert "does not exist" in capsys.readouterr().out.lower()


def test_registration_adds_feedback_subcommand():
    parser = _build_parser()
    # Parsing without a subcommand under `feedback` must error.
    with pytest.raises(SystemExit):
        parser.parse_args(["feedback"])
