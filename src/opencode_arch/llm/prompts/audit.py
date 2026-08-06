"""Prompt templates for LLM functional-decomposition audit."""

AUDIT_STAGE1_VERSION = "v1"

AUDIT_STAGE1_TEMPLATE = """You are analyzing a codebase to identify its functional subsystems.

## Source Code Structure
{source_summary}

## Project Context
{context_md}

Based ONLY on the code structure, imports, and documentation above, identify the distinct functional subsystems (groups of files that work together to accomplish a specific purpose).

For each subsystem, provide:
1. A short descriptive name
2. Which files belong to it
3. A one-sentence rationale explaining why these files form a coherent unit

Return your analysis as JSON:
```json
{{
  "blocks": [
    {{"id": "LLM-A", "name": "...", "files": ["..."], "rationale": "..."}}
  ]
}}
```
"""

AUDIT_STAGE2_VERSION = "v1"

AUDIT_STAGE2_TEMPLATE = """You previously identified these functional subsystems:

{llm_decomposition}

The automated tool produced this decomposition with these quality metrics:

{tool_decomposition}

Modularity (Newman's Q): {modularity}
Per-block conductance: {conductance}

Compare your grouping with the tool's. For each pair:
- If they substantially agree (>70% file overlap), mark as "agree"
- If they disagree, explain WHY with specific evidence (naming conventions, documented boundaries, import patterns)

Return as JSON:
```json
{{
  "agreement_rate": 0.71,
  "matched_pairs": [
    {{"tool_source_block": "S1", "llm_block": "LLM-A", "overlap": 0.9, "verdict": "agree"}}
  ],
  "disagreements": [
    {{
      "tool_source_block": "S3",
      "llm_block": "LLM-C",
      "overlap": 0.4,
      "llm_rationale": "...",
      "cites_doc": "README.md#L42",
      "recommendation": "flag_for_review"
    }}
  ]
}}
```
"""
