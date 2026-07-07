"""Tests for report card generation."""
import pytest

from opencode_arch.learning.assessor import generate_report_card, _compute_grade, ReportCard


class TestGrading:
    def test_grade_a(self):
        assert _compute_grade(0.95, 6.0, 0) == "A"

    def test_grade_b(self):
        assert _compute_grade(0.80, 4.0, 1) == "B"

    def test_grade_c(self):
        assert _compute_grade(0.65, 2.0, 2) == "C"

    def test_grade_d(self):
        assert _compute_grade(0.45, 1.0, 5) == "D"

    def test_grade_f(self):
        assert _compute_grade(0.30, 1.0, 0) == "F"


class TestReportCard:
    def test_perfect_run(self):
        results = {
            "ansi": {"converged": True, "pass_rate": 1.0, "time_seconds": 30,
                     "features": {"constant_count": 10, "signature_count": 5, "contract_count": 20},
                     "token_metrics": {"compression_ratio": 8.0}},
            "utils": {"converged": True, "pass_rate": 1.0, "time_seconds": 25,
                      "features": {"constant_count": 5, "signature_count": 3, "contract_count": 15},
                      "token_metrics": {"compression_ratio": 6.0}},
        }
        card = generate_report_card("colorama", "blind", results)
        assert card.grade == "A"
        assert card.fidelity == 1.0
        assert card.compression_ratio == 7.0
        assert card.fidelity_trend == "STABLE"

    def test_partial_failure(self):
        results = {
            "sub1": {"converged": True, "pass_rate": 1.0, "time_seconds": 30,
                     "features": {"constant_count": 10, "signature_count": 5, "contract_count": 20},
                     "token_metrics": {"compression_ratio": 5.0}},
            "sub2": {"converged": False, "pass_rate": 0.3, "time_seconds": 50,
                     "features": {"constant_count": 2, "signature_count": 15, "contract_count": 5},
                     "token_metrics": {"compression_ratio": 4.0},
                     "failure_patterns": {"cross_dep": 3}},
            "sub3": {"converged": False, "pass_rate": 0.0, "time_seconds": 60,
                     "features": {"constant_count": 0, "signature_count": 20, "contract_count": 0},
                     "token_metrics": {"compression_ratio": 3.0},
                     "failure_patterns": {"cross_dep": 2, "unknown": 1}},
        }
        card = generate_report_card("structlog", "blind", results)
        assert card.fidelity == pytest.approx(1/3)
        assert card.novel_patterns == 1
        assert "cross_dep" in card.failure_patterns
        assert card.grade == "F"  # <40% fidelity

    def test_trend_detection(self):
        results = {
            "sub1": {"converged": True, "pass_rate": 1.0, "time_seconds": 30,
                     "features": {}, "token_metrics": {"compression_ratio": 5.0}},
        }
        card = generate_report_card("tqdm", "blind", results, previous_fidelity=0.7)
        assert card.fidelity_trend == "UP"

    def test_improvement_actions_generated(self):
        results = {
            "sub1": {"converged": False, "pass_rate": 0.3, "time_seconds": 50,
                     "features": {}, "token_metrics": {"compression_ratio": 2.0},
                     "failure_patterns": {"cross_dep": 5}},
        }
        card = generate_report_card("repo", "blind", results)
        assert len(card.improvement_actions) > 0
        assert any("dep" in a.lower() for a in card.improvement_actions)
