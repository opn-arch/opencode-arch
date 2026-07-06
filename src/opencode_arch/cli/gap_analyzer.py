"""Gap analyzer — maps test failure output to actionable feedback for the next iteration."""
from __future__ import annotations

import re


# Common failure patterns and their interpretations
_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"NameError: name '(\w+)' is not defined"),
     "Missing symbol: {0}"),
    (re.compile(r"ImportError: cannot import name '(\w+)' from '(\w+)'"),
     "Missing export: '{0}' not available in module '{1}'"),
    (re.compile(r"ModuleNotFoundError: No module named '(\S+)'"),
     "Missing module: {0}"),
    (re.compile(r"AttributeError: (?:type object |)'(\w+)' (?:object )?has no attribute '(\w+)'"),
     "Missing attribute '{1}' on '{0}'"),
    (re.compile(r"AttributeError: module '(\w+)' has no attribute '(\w+)'"),
     "Missing attribute '{1}' on module '{0}'"),
    (re.compile(r"AssertionError: (.+?) != (.+)"),
     "Wrong value: got {0}, expected {1}"),
    (re.compile(r"AssertionError: (False|0) is not true"),
     "Assertion failed: expression evaluated to False"),
    (re.compile(r"TypeError: (\w+)\(\) (?:takes|got|missing) (.+)"),
     "Signature mismatch for {0}: {1}"),
    (re.compile(r"TypeError: (\w+)\(\) (.+)"),
     "Type error in {0}: {1}"),
    (re.compile(r"KeyError: '(\w+)'"),
     "Missing key: '{0}'"),
    (re.compile(r"ValueError: (.+)"),
     "Value error: {0}"),
    (re.compile(r"IndentationError: (.+)"),
     "Syntax issue: indentation error — {0}"),
    (re.compile(r"SyntaxError: (.+)"),
     "Syntax error: {0}"),
]


def analyze_gaps(test_output: str, model_context: str = "") -> str:
    """Parse test failure output and produce enrichment feedback.

    Maps common failure patterns to structured feedback for the next
    iteration prompt. Returns a formatted string summarizing what needs
    fixing.

    Args:
        test_output: Raw pytest output (stdout + stderr).
        model_context: Optional architecture model context for cross-referencing.

    Returns:
        Formatted feedback string with identified gaps.
    """
    if not test_output.strip():
        return "No test output to analyze."

    gaps: list[str] = []
    seen: set[str] = set()

    for line in test_output.splitlines():
        line_stripped = line.strip()
        for pattern, template in _PATTERNS:
            m = pattern.search(line_stripped)
            if m:
                msg = template.format(*m.groups())
                if msg not in seen:
                    seen.add(msg)
                    gaps.append(f"- {msg}")
                break  # One pattern per line

    # Extract FAILED test names for additional context
    failed_tests = _extract_failed_tests(test_output)
    if failed_tests:
        gaps.append("")
        gaps.append("Failed tests:")
        for t in failed_tests[:20]:  # Cap at 20
            gaps.append(f"  - {t}")

    if not gaps:
        # Generic fallback
        return _generic_feedback(test_output)

    return "\n".join(gaps)


def _extract_failed_tests(output: str) -> list[str]:
    """Extract FAILED test names from pytest output."""
    failed: list[str] = []
    for line in output.splitlines():
        # pytest FAILED line: "FAILED test_file.py::test_name - ..."
        if line.startswith("FAILED "):
            parts = line.split(" - ", 1)
            name = parts[0].replace("FAILED ", "").strip()
            failed.append(name)
        # Short test summary: "FAILED test_x.py::test_y"
        elif "FAILED" in line and "::" in line:
            match = re.search(r"FAILED\s+([\w/.]+::\w+)", line)
            if match:
                failed.append(match.group(1))
    return list(dict.fromkeys(failed))  # dedupe preserving order


def _generic_feedback(output: str) -> str:
    """Produce generic feedback when no specific patterns match."""
    # Look for the short summary line
    for line in output.splitlines():
        if "failed" in line.lower() and ("passed" in line.lower() or "error" in line.lower()):
            return f"Tests failed but no specific error patterns matched.\nSummary: {line.strip()}\nReview the test assertions and ensure all expected values match."
    return "Tests failed. Review the output and ensure all assertions pass."
