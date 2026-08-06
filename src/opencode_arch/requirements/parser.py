from __future__ import annotations
import re, hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExtractedRequirement:
    id: str
    text: str
    source_doc: str
    source_anchor: str
    content_hash: str
    extraction_method: str  # "structural", "llm", "retroactive", "llm_matched"


def parse_requirements_doc(doc_path: Path) -> list[ExtractedRequirement]:
    """Parse structured requirements from a document.

    Recognizes:
    - REQ-NNN: text (ID-prefixed lines)
    - ### Requirement: text (heading-based)
    - - [ ] / - [x] checkbox items with REQ- prefix
    """
    content = doc_path.read_text()
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    results: list[ExtractedRequirement] = []

    # Pattern 1: REQ-NNN: description
    for match in re.finditer(r'^(REQ-\d+)[:\s]+(.+?)$', content, re.MULTILINE):
        req_id, text = match.group(1), match.group(2).strip()
        line_num = content[:match.start()].count('\n') + 1
        results.append(ExtractedRequirement(
            id=req_id, text=text, source_doc=str(doc_path),
            source_anchor=f"L{line_num}", content_hash=content_hash,
            extraction_method="structural",
        ))

    # Pattern 2: ### Requirement: text (assign auto IDs if no REQ- prefix)
    if not results:
        auto_id = 1
        for match in re.finditer(r'^#{1,4}\s+Requirement[:\s]+(.+?)$', content, re.MULTILINE):
            text = match.group(1).strip()
            line_num = content[:match.start()].count('\n') + 1
            results.append(ExtractedRequirement(
                id=f"REQ-{auto_id:03d}", text=text, source_doc=str(doc_path),
                source_anchor=f"L{line_num}", content_hash=content_hash,
                extraction_method="structural",
            ))
            auto_id += 1

    # Pattern 3: Checkbox items with REQ prefix
    if not results:
        for match in re.finditer(r'^-\s+\[[ x]\]\s+(REQ-\d+)[:\s]+(.+?)$', content, re.MULTILINE):
            req_id, text = match.group(1), match.group(2).strip()
            line_num = content[:match.start()].count('\n') + 1
            results.append(ExtractedRequirement(
                id=req_id, text=text, source_doc=str(doc_path),
                source_anchor=f"L{line_num}", content_hash=content_hash,
                extraction_method="structural",
            ))

    return results
