"""Tests for the regen prompt templates."""
import pytest

from opencode_arch.prompts.regen import REGEN_PROMPT, FEEDBACK_HEADER


class TestRegenPrompt:
    def test_template_has_required_placeholders(self):
        """REGEN_PROMPT should contain all expected format keys."""
        required = [
            "{subsystem_name}",
            "{iteration}",
            "{max_iterations}",
            "{source_files}",
            "{model_context}",
            "{constants}",
            "{signatures}",
            "{test_contracts}",
            "{dependency_apis}",
            "{previous_feedback}",
        ]
        for key in required:
            assert key in REGEN_PROMPT, f"Missing placeholder: {key}"

    def test_format_basic(self):
        """Should format without errors."""
        result = REGEN_PROMPT.format(
            subsystem_name="core",
            iteration=1,
            max_iterations=5,
            source_files="- core.py",
            model_context="Component: Core",
            constants="- VERSION = '1.0'",
            signatures="- init(self)",
            test_contracts="- [value_equality] x == 1",
            dependency_apis="(none)",
            previous_feedback="",
        )
        assert "core" in result
        assert "iteration 1/5" in result

    def test_feedback_header(self):
        """FEEDBACK_HEADER should format correctly."""
        result = FEEDBACK_HEADER.format(
            prev_iteration=2,
            failure_analysis="- Missing symbol: Foo",
        )
        assert "iteration (2)" in result
        assert "Missing symbol: Foo" in result
