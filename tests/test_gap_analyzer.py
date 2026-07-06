"""Tests for gap_analyzer module."""
import pytest

from opencode_arch.cli.gap_analyzer import analyze_gaps, _extract_failed_tests


class TestAnalyzeGaps:
    def test_name_error(self):
        output = "NameError: name 'Fore' is not defined"
        result = analyze_gaps(output)
        assert "Missing symbol: Fore" in result

    def test_import_error(self):
        output = "ImportError: cannot import name 'Style' from 'colorama'"
        result = analyze_gaps(output)
        assert "Missing export" in result
        assert "'Style'" in result

    def test_module_not_found(self):
        output = "ModuleNotFoundError: No module named 'colorama'"
        result = analyze_gaps(output)
        assert "Missing module: colorama" in result

    def test_attribute_error(self):
        output = "AttributeError: 'Fore' object has no attribute 'RESET'"
        result = analyze_gaps(output)
        assert "Missing attribute 'RESET' on 'Fore'" in result

    def test_assertion_error_value(self):
        output = "AssertionError: '\\033[30m' != '\\033[31m'"
        result = analyze_gaps(output)
        assert "Wrong value" in result

    def test_type_error(self):
        output = "TypeError: add() takes 2 positional arguments but 3 were given"
        result = analyze_gaps(output)
        assert "Signature mismatch" in result or "Type error" in result

    def test_key_error(self):
        output = "KeyError: 'name'"
        result = analyze_gaps(output)
        assert "Missing key: 'name'" in result

    def test_syntax_error(self):
        output = "SyntaxError: unexpected EOF while parsing"
        result = analyze_gaps(output)
        assert "Syntax error" in result

    def test_multiple_errors(self):
        output = (
            "NameError: name 'Fore' is not defined\n"
            "AttributeError: 'Style' object has no attribute 'RESET'\n"
            "ImportError: cannot import name 'Back' from 'colorama'\n"
        )
        result = analyze_gaps(output)
        assert "Missing symbol: Fore" in result
        assert "Missing attribute 'RESET' on 'Style'" in result
        assert "Missing export" in result

    def test_deduplication(self):
        output = (
            "NameError: name 'X' is not defined\n"
            "NameError: name 'X' is not defined\n"
        )
        result = analyze_gaps(output)
        assert result.count("Missing symbol: X") == 1

    def test_empty_output(self):
        result = analyze_gaps("")
        assert "No test output" in result

    def test_failed_tests_extraction(self):
        output = (
            "FAILED test_foo.py::test_bar - AssertionError\n"
            "FAILED test_baz.py::test_qux - NameError\n"
        )
        result = analyze_gaps(output)
        assert "test_foo.py::test_bar" in result
        assert "test_baz.py::test_qux" in result

    def test_generic_fallback(self):
        output = "something happened\n2 failed, 1 passed in 0.5s"
        result = analyze_gaps(output)
        assert "failed" in result.lower()


class TestExtractFailedTests:
    def test_standard_format(self):
        output = "FAILED test_foo.py::test_one - Error\nFAILED test_bar.py::test_two - Error"
        result = _extract_failed_tests(output)
        assert "test_foo.py::test_one" in result
        assert "test_bar.py::test_two" in result

    def test_deduplication(self):
        output = "FAILED test_x.py::test_a - Err\nFAILED test_x.py::test_a - Err"
        result = _extract_failed_tests(output)
        assert len(result) == 1

    def test_no_failures(self):
        output = "5 passed in 0.3s"
        result = _extract_failed_tests(output)
        assert result == []
