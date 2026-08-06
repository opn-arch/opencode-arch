"""Prompt templates for function-requirement matching."""

MATCHING_TEMPLATE = """\
Match the following functions to the requirements they satisfy.
For each match, provide the function ID, requirement ID, a confidence score (0.0-1.0),
and evidence explaining the match.

Requirements:
{requirements_text}

Functions (from architecture model):
{functions_text}

Return a JSON object with a "matches" key containing an array of objects,
each with "function_id", "requirement_id", "confidence", and "evidence" fields.

Return ONLY valid JSON. Example:
{{"matches": [{{"function_id": "COMP-1", "requirement_id": "REQ-001", "confidence": 0.85, "evidence": "Component handles user authentication"}}]}}
"""

MATCHING_VERSION = "req-match-v1"
