"""Metrics and report commands - display recorded telemetry."""
from __future__ import annotations

import json
import time

from opencode_arch.telemetry.store import TelemetryStore


def show_metrics(
    tool: str | None = None,
    last: int = 10,
    learning_curve: bool = False,
    drift: bool = False,
):
    """Query and display metrics from the telemetry store."""
    store = TelemetryStore()

    if learning_curve:
        _show_learning_curve(store)
        return

    if drift:
        _show_drift_flags(store)
        return

    records = store.query(tool=tool, limit=last)
    print(format_metrics_table(records))
    if tool and records:
        avgs = store.averages(tool=tool)
        print(f"\n  Averages for '{tool}':")
        print(f"    Tokens:     {avgs['avg_context_tokens']:.0f}")
        print(f"    Quality:    {avgs['avg_output_quality']:.0f}/100")
        print(f"    Iterations: {avgs['avg_iterations']:.1f}")


def show_report(repo: str | None = None, last: int = 5):
    """Display report cards from telemetry."""
    store = TelemetryStore()
    cards = store.get_report_cards(repo=repo, limit=last)

    if not cards:
        print("  No report cards found.")
        return

    print(f"\nReport Cards (last {last})")
    print("=" * 70)

    for card in cards:
        grade = card.get("grade", "?")
        repo_name = card.get("repo", "?")
        mode = card.get("mode", "?")
        fidelity = card.get("fidelity", 0.0)
        compression = card.get("compression_ratio", 0.0)
        novel = card.get("novel_patterns", 0)
        ts = card.get("timestamp", "")[:10]  # date only

        # Grade color indicator
        grade_indicator = {"A": "+", "B": "+", "C": "~", "D": "-", "F": "!"}
        indicator = grade_indicator.get(grade, "?")

        print(f"\n  [{indicator}] Grade {grade} | {repo_name} ({mode}) | {ts}")
        print(f"      Fidelity:    {fidelity:.0%}")
        print(f"      Compression: {compression:.1f}x")
        if novel > 0:
            print(f"      Novel:       {novel} unclassified patterns")

        # Failure patterns
        patterns_str = card.get("failure_patterns", "{}")
        try:
            patterns = json.loads(patterns_str) if isinstance(patterns_str, str) else patterns_str
            if patterns:
                print(f"      Patterns:    {', '.join(f'{k}={v}' for k, v in patterns.items())}")
        except (json.JSONDecodeError, TypeError):
            pass

        # Improvement actions
        actions_str = card.get("improvement_actions", "[]")
        try:
            actions = json.loads(actions_str) if isinstance(actions_str, str) else actions_str
            if actions:
                print(f"      Actions:")
                for action in actions:
                    print(f"        - {action}")
        except (json.JSONDecodeError, TypeError):
            pass

    # Also show lessons if available
    lessons = store.get_lessons()
    if lessons:
        print(f"\n\nLessons Learned ({len(lessons)} total)")
        print("-" * 50)
        for lesson in lessons[:10]:
            cat = lesson.get("category", "?")
            desc = lesson.get("description", "?")
            repo_name = lesson.get("discovered_repo", "?")
            print(f"  [{cat:12}] {desc}")
            print(f"               (from {repo_name})")


def _show_learning_curve(store: TelemetryStore):
    """Display learning curve data showing improvement over repos."""
    entries = store.get_learning_curve()

    if not entries:
        print("  No learning curve data yet.")
        return

    print(f"\nLearning Curve ({len(entries)} repos processed)")
    print("=" * 80)
    print(f"  {'#':<3} {'Repo':<15} {'Mode':<7} {'Conv':>5} {'Pass%':>6} "
          f"{'Iter':>5} {'Compress':>9} {'Time':>7}")
    print("  " + "-" * 75)

    for entry in entries:
        seq = entry.get("repo_sequence", 0)
        repo = entry.get("repo", "?")[:14]
        mode = entry.get("mode", "?")
        total = entry.get("total_subsystems", 0)
        conv = entry.get("converged_subsystems", 0)
        pass_rate = entry.get("avg_pass_rate", 0)
        iters = entry.get("avg_iterations", 0)
        compression = entry.get("avg_compression_ratio", 0)
        time_s = entry.get("total_time_seconds", 0)

        conv_str = f"{conv}/{total}"
        print(f"  {seq:<3} {repo:<15} {mode:<7} {conv_str:>5} {pass_rate:>5.0%} "
              f"{iters:>5.1f} {compression:>8.1f}x {time_s:>6.0f}s")

    # Trend summary
    if len(entries) >= 2:
        first = entries[0]
        last = entries[-1]
        fid_first = first.get("converged_subsystems", 0) / max(first.get("total_subsystems", 1), 1)
        fid_last = last.get("converged_subsystems", 0) / max(last.get("total_subsystems", 1), 1)
        comp_first = first.get("avg_compression_ratio", 0)
        comp_last = last.get("avg_compression_ratio", 0)

        print(f"\n  Trends:")
        fid_arrow = "^" if fid_last > fid_first else "v" if fid_last < fid_first else "="
        comp_arrow = "^" if comp_last > comp_first else "v" if comp_last < comp_first else "="
        print(f"    Fidelity:    {fid_first:.0%} -> {fid_last:.0%} [{fid_arrow}]")
        print(f"    Compression: {comp_first:.1f}x -> {comp_last:.1f}x [{comp_arrow}]")


def _show_drift_flags(store: TelemetryStore):
    """Display unresolved documentation drift flags."""
    flags = store.get_drift_flags(resolved=False)

    if not flags:
        print("  No unresolved drift flags. Documentation is in sync.")
        return

    print(f"\nDocumentation Drift ({len(flags)} unresolved)")
    print("=" * 70)

    for flag in flags:
        severity = flag.get("severity", "?")
        file_path = flag.get("file", "?")
        issue = flag.get("issue", "?")
        fixable = "auto-fixable" if flag.get("auto_fixable") else "manual"
        suggested = flag.get("suggested_fix", "")

        sev_indicator = {"blocker": "!!", "high": "!", "medium": "~", "low": "."}
        indicator = sev_indicator.get(severity, "?")

        print(f"\n  [{indicator}] {severity.upper():8} {file_path}")
        print(f"      Issue: {issue}")
        print(f"      Fix:   {suggested} ({fixable})")


def format_metrics_table(records: list[dict]) -> str:
    """Format records as a readable table."""
    if not records:
        return "  No records found."
    lines = []
    lines.append(f"  {'Tool':<18} {'Repo':<25} {'Score':>5} {'Tokens':>6} {'Iter':>4} {'Time'}")
    lines.append("  " + "-" * 75)
    for r in records:
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(r.get("timestamp", 0)))
        lines.append(
            f"  {r.get('tool', '?'):<18} {r.get('repo', '?'):<25} "
            f"{r.get('output_quality', 0):>5} {r.get('context_tokens', 0):>6} "
            f"{r.get('iterations', 0):>4} {ts}"
        )
    return "\n".join(lines)
