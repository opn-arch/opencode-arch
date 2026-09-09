"""Phase 2 Task 20 — ``opencode-arch feedback`` subcommands.

Currently exposes one command:

    opencode-arch feedback ingest-junit <junit.xml> [--repo-path .] [--suite NAME]

Reads a JUnit XML file, delegates to
:func:`architecture_model.feedback.junit_ingest.ingest_junit`, then
appends the resulting :class:`TestResultBatch` to
``<repo>/.architecture/test_results.jsonl`` via
:func:`architecture_model.feedback.test_results.append`.

The subcommand follows the argparse pattern used by the rest of the
opencode-arch CLI (deviation from plan, which specified click — the
existing CLI is 100% argparse).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def register_feedback_subparsers(subparsers) -> None:
    """Register ``feedback`` and its subcommands on ``subparsers``."""
    feedback_p = subparsers.add_parser(
        "feedback",
        help="Ingest external feedback signals (JUnit, gates, drift)",
    )
    feedback_sub = feedback_p.add_subparsers(dest="feedback_command", required=True)

    junit_p = feedback_sub.add_parser(
        "ingest-junit",
        help="Ingest a JUnit XML file into .architecture/test_results.jsonl",
    )
    junit_p.add_argument("junit_xml", help="Path to the JUnit XML file")
    junit_p.add_argument(
        "--repo-path",
        default=".",
        help="Repository root (defaults to the current directory)",
    )
    junit_p.add_argument(
        "--suite",
        default=None,
        help="Optional suite name override (defaults to XML root name)",
    )


def dispatch_feedback(args: argparse.Namespace) -> int:
    """Dispatch on ``args.feedback_command``. Returns process exit code."""
    if args.feedback_command == "ingest-junit":
        return _cmd_ingest_junit(args)
    print(f"Unknown feedback subcommand: {args.feedback_command}")
    return 2


def _cmd_ingest_junit(args: argparse.Namespace) -> int:
    from architecture_model.feedback.junit_ingest import ingest_junit
    from architecture_model.feedback.test_results import append as _tr_append

    junit_path = Path(args.junit_xml)
    repo_path = Path(args.repo_path).resolve()

    if not junit_path.exists():
        print(f"error: JUnit file not found: {junit_path}")
        return 1
    if not repo_path.exists():
        print(f"error: repo-path does not exist: {repo_path}")
        return 1

    try:
        batch = ingest_junit(junit_path, suite=args.suite)
    except Exception as e:
        print(f"error: failed to parse JUnit XML: {e}")
        return 1

    try:
        _tr_append(repo_path, batch)
    except Exception as e:
        print(f"error: failed to append to test_results.jsonl: {e}")
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "suite": batch.suite,
                "total": batch.total,
                "passed": batch.passed,
                "failed": batch.failed,
                "skipped": batch.skipped,
                "duration_s": batch.duration_s,
                "failure_count": len(batch.failures),
                "journal": str(repo_path / ".architecture" / "test_results.jsonl"),
            }
        )
    )
    return 0


__all__ = ["register_feedback_subparsers", "dispatch_feedback"]
