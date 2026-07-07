"""Tests for lesson extraction."""
import pytest

from opencode_arch.learning.lessons import extract_lessons, _make_lesson_id


class TestLessonExtraction:
    def test_extracts_contract_threshold_lesson(self):
        results = {
            "good1": {"converged": True, "features": {"contract_count": 50, "signature_count": 5, "constant_count": 10}},
            "good2": {"converged": True, "features": {"contract_count": 40, "signature_count": 8, "constant_count": 5}},
            "bad1": {"converged": False, "features": {"contract_count": 5, "signature_count": 20, "constant_count": 2},
                     "failure_patterns": {}},
        }
        lessons = extract_lessons("structlog", "blind", results)
        pattern_lessons = [l for l in lessons if l.category == "pattern"]
        assert len(pattern_lessons) >= 1
        assert any("contract" in l.description.lower() for l in pattern_lessons)

    def test_extracts_simple_success_lesson(self):
        results = {
            f"simple{i}": {"converged": True, "features": {"signature_count": 5, "contract_count": 20, "constant_count": 3}}
            for i in range(4)
        }
        lessons = extract_lessons("tqdm", "blind", results)
        success_lessons = [l for l in lessons if l.category == "success"]
        assert len(success_lessons) >= 1

    def test_no_lessons_from_all_converged(self):
        results = {
            "sub1": {"converged": True, "features": {"contract_count": 30, "signature_count": 10, "constant_count": 5}},
            "sub2": {"converged": True, "features": {"contract_count": 25, "signature_count": 8, "constant_count": 4}},
        }
        lessons = extract_lessons("easy_repo", "normal", results)
        # Should still get success lesson if enough simple subsystems
        limitation_lessons = [l for l in lessons if l.category == "limitation"]
        assert len(limitation_lessons) == 0

    def test_lesson_id_stable(self):
        id1 = _make_lesson_id("pattern", "test description")
        id2 = _make_lesson_id("pattern", "test description")
        assert id1 == id2  # deterministic

    def test_dominant_pattern_lesson(self):
        results = {
            "bad1": {"converged": False, "features": {"contract_count": 5, "signature_count": 10, "constant_count": 2},
                     "failure_patterns": {"cross_dep": 5}},
            "bad2": {"converged": False, "features": {"contract_count": 3, "signature_count": 12, "constant_count": 1},
                     "failure_patterns": {"cross_dep": 4}},
            "good": {"converged": True, "features": {"contract_count": 20, "signature_count": 5, "constant_count": 10}},
        }
        lessons = extract_lessons("structlog", "blind", results)
        pattern_lessons = [l for l in lessons if "dominant" in l.description.lower()]
        assert len(pattern_lessons) >= 1
