"""Tests for the dual-level failure pattern classifier."""
import pytest

from opencode_arch.learning.classifier import classify_failures, _classify_raw, _classify_structured
from opencode_arch.learning.patterns import PatternType, Strategy


class TestRawClassification:
    """Test Level 1: regex-based classification."""

    def test_import_error_classified_as_cross_dep(self):
        output = "ImportError: cannot import name 'BoundLogger' from 'structlog._base'"
        results = _classify_raw(output)
        assert len(results) >= 1
        assert results[0].pattern == PatternType.CROSS_DEP
        assert results[0].confidence >= 0.9
        assert "BoundLogger" in results[0].affected_symbols

    def test_module_not_found_classified_as_cross_dep(self):
        output = "ModuleNotFoundError: No module named 'tqdm.utils'"
        results = _classify_raw(output)
        assert any(c.pattern == PatternType.CROSS_DEP for c in results)

    def test_attribute_error_classified_as_missing_impl(self):
        output = "AttributeError: module 'colorama' has no attribute 'init'"
        results = _classify_raw(output)
        assert any(c.pattern == PatternType.MISSING_IMPL for c in results)

    def test_assertion_literal_classified_as_wrong_constant(self):
        output = "AssertionError: assert 'RED' == 'red'"
        results = _classify_raw(output)
        assert any(c.pattern == PatternType.WRONG_CONSTANT for c in results)

    def test_type_error_classified_as_api_mismatch(self):
        output = "TypeError: configure() takes 2 positional arguments but 3 were given"
        results = _classify_raw(output)
        assert any(c.pattern == PatternType.API_MISMATCH for c in results)

    def test_test_helper_import_classified_as_test_infra(self):
        output = "ModuleNotFoundError: No module named 'tests.helpers'"
        results = _classify_raw(output)
        assert any(c.pattern == PatternType.TEST_INFRA for c in results)

    def test_deduplicates_same_pattern_same_symbol(self):
        output = (
            "ImportError: cannot import name 'Foo' from 'bar'\n"
            "ImportError: cannot import name 'Foo' from 'bar'"
        )
        results = _classify_raw(output)
        foo_results = [r for r in results if "Foo" in r.affected_symbols]
        assert len(foo_results) == 1

    def test_multiple_patterns_detected(self):
        output = (
            "ImportError: cannot import name 'X' from 'mod'\n"
            "AttributeError: 'Y' object has no attribute 'z'\n"
        )
        results = _classify_raw(output)
        patterns = {r.pattern for r in results}
        assert PatternType.CROSS_DEP in patterns
        assert PatternType.MISSING_IMPL in patterns


class TestStructuredClassification:
    """Test Level 2: structured classification."""

    def test_complex_behavior_detected_on_many_failures(self):
        results = _classify_structured("", pass_rate=0.3, total_tests=20, failed_tests=14)
        assert any(c.pattern == PatternType.COMPLEX_BEHAVIOR for c in results)

    def test_no_complex_behavior_on_few_failures(self):
        results = _classify_structured("", pass_rate=0.8, total_tests=10, failed_tests=2)
        assert not any(c.pattern == PatternType.COMPLEX_BEHAVIOR for c in results)

    def test_import_dominated_failures_classified_as_cross_dep(self):
        output = "ImportError\n" * 8 + "AssertionError\n" * 2
        results = _classify_structured(output, pass_rate=0.0, total_tests=10, failed_tests=10)
        assert any(c.pattern == PatternType.CROSS_DEP for c in results)


class TestCombinedClassification:
    """Test the combined classify_failures function."""

    def test_returns_sorted_by_confidence(self):
        output = (
            "ImportError: cannot import name 'X' from 'mod'\n"
            "AssertionError: assert 1 == 2\n"
        )
        results = classify_failures(output, pass_rate=0.5, total_tests=10, failed_tests=5)
        if len(results) >= 2:
            assert results[0].confidence >= results[1].confidence

    def test_empty_output_returns_empty(self):
        results = classify_failures("", pass_rate=1.0, total_tests=10, failed_tests=0)
        assert results == []

    def test_strategies_assigned(self):
        output = "ImportError: cannot import name 'Foo' from 'bar'"
        results = classify_failures(output)
        assert results[0].suggested_strategy == Strategy.EXPAND_DEP_CONTEXT
