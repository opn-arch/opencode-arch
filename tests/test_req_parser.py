"""Tests for deterministic requirement parser."""
import hashlib
from pathlib import Path

import pytest

from opencode_arch.requirements.parser import parse_requirements_doc


@pytest.fixture
def tmp_doc(tmp_path):
    """Helper to write a temp doc and return its path."""
    def _write(content: str) -> Path:
        p = tmp_path / "requirements.md"
        p.write_text(content)
        return p
    return _write


class TestReqPrefixedLines:
    def test_parses_req_lines(self, tmp_doc):
        doc = tmp_doc("# Reqs\nREQ-001: System shall authenticate users\nREQ-002: System shall log events\n")
        results = parse_requirements_doc(doc)
        assert len(results) == 2
        assert results[0].id == "REQ-001"
        assert results[0].text == "System shall authenticate users"
        assert results[0].extraction_method == "structural"
        assert results[0].source_anchor == "L2"
        assert results[1].id == "REQ-002"
        assert results[1].source_anchor == "L3"


class TestHeadingBased:
    def test_heading_requirements(self, tmp_doc):
        doc = tmp_doc("### Requirement: Must support SSO\n### Requirement: Must export CSV\n")
        results = parse_requirements_doc(doc)
        assert len(results) == 2
        assert results[0].id == "REQ-001"
        assert results[0].text == "Must support SSO"
        assert results[1].id == "REQ-002"
        assert results[1].text == "Must export CSV"


class TestCheckboxItems:
    def test_checkbox_requirements(self, tmp_doc):
        doc = tmp_doc("- [x] REQ-010: Implement caching\n- [ ] REQ-011: Add rate limiting\n")
        results = parse_requirements_doc(doc)
        assert len(results) == 2
        assert results[0].id == "REQ-010"
        assert results[0].text == "Implement caching"
        assert results[1].id == "REQ-011"


class TestEmptyDoc:
    def test_empty_returns_empty(self, tmp_doc):
        doc = tmp_doc("")
        results = parse_requirements_doc(doc)
        assert results == []


class TestContentHash:
    def test_hash_is_deterministic(self, tmp_doc):
        content = "REQ-001: Test requirement\n"
        doc = tmp_doc(content)
        r1 = parse_requirements_doc(doc)
        r2 = parse_requirements_doc(doc)
        assert r1[0].content_hash == r2[0].content_hash
        expected = hashlib.sha256(content.encode()).hexdigest()[:16]
        assert r1[0].content_hash == expected
