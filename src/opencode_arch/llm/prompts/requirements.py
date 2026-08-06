"""Prompt templates for requirement extraction."""

REQUIREMENTS_EXTRACT_TEMPLATE = """\
Analyze the following document and identify all distinct requirements.
Return a JSON object with a "requirements" key containing an array of objects,
each with "id", "text", and "anchor" fields.

- "id": Use any existing REQ-NNN ID found in the text, or assign one as REQ-001, REQ-002, etc.
- "text": The requirement statement (concise, imperative).
- "anchor": The line reference or section where it appears (e.g., "L5", "Section 2").

Document content:
---
{doc_content}
---

Return ONLY valid JSON. Example:
{{"requirements": [{{"id": "REQ-001", "text": "System shall support login", "anchor": "L3"}}]}}
"""

REQUIREMENTS_EXTRACT_VERSION = "req-extract-v1"


REQUIREMENTS_RETROACTIVE_TEMPLATE = """\
Given the following architecture model, derive requirements that the system must satisfy.
Look at capabilities, behaviors, interfaces, and component responsibilities.
Return a JSON object with a "requirements" key containing an array of objects,
each with "id", "text", and "source" fields.

- "id": Assign as REQ-001, REQ-002, etc.
- "text": The derived requirement (concise, imperative, testable).
- "source": Which model element (capability/behavior/interface) this derives from.

Architecture model:
---
{model_yaml}
---

Return ONLY valid JSON. Example:
{{"requirements": [{{"id": "REQ-001", "text": "System shall validate input", "source": "CAP-F1"}}]}}
"""

REQUIREMENTS_RETROACTIVE_VERSION = "req-retro-v1"
