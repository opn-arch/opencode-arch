"""Prompt templates for agent invocation."""

EXTRACT_PROMPT = """\
Extract the architecture of the repository at: {repo_path}

Focus: {focus}
Token budget: {budget}
Target validation score: {target_score}+

Use the architect_scan, architect_slice, architect_validate, and architect_extract tools to complete the extraction. Output the final YAML model between ```yaml fences.
"""

GENERATE_PROMPT = """\
Generate code for the repository at: {repo_path}

Use architect_scan and architect_slice to understand the architecture.
Then generate code that passes the test suite.
Use architect_generate to run tests and verify.
Iterate on failures (max {max_iter} attempts).
"""
