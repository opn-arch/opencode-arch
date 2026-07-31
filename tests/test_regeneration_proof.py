"""Tests for regeneration proof functions."""
from opencode_arch.cli.calibrate import format_regeneration_prompt, compare_regeneration


def test_format_regeneration_prompt_includes_model_context():
    ctx = {
        "id": "COMP-1",
        "name": "Scheduler",
        "contract": "Manages task scheduling",
        "pattern": "Observer",
        "signatures": [{"name": "schedule", "params": ["task", "delay"], "returns": "bool"}],
        "symbols": [{"name": "TaskQueue", "kind": "class", "members": ["push", "pop"]}],
        "constants": [{"name": "MAX_TASKS", "value": "100"}],
        "responsibilities": ["Queue tasks", "Execute on time"],
    }
    prompt = format_regeneration_prompt(ctx)
    assert "DO NOT read source files" in prompt
    assert "Scheduler" in prompt
    assert "COMP-1" in prompt
    assert "Manages task scheduling" in prompt
    assert "Observer" in prompt
    assert "schedule" in prompt
    assert "TaskQueue" in prompt
    assert "MAX_TASKS" in prompt
    assert "Queue tasks" in prompt
    assert "Python module" in prompt


def test_compare_regeneration_measures_api_compatibility():
    original = "def schedule(): pass\ndef cancel(): pass\n"
    generated = "def schedule(): pass\ndef cancel(): pass\ndef status(): pass\n"
    result = compare_regeneration(original, generated)
    assert result["api_coverage"] >= 0.8
    assert "status" in result["extra_apis"]
    assert result["missing_apis"] == []


def test_compare_regeneration_detects_missing_apis():
    original = "def bar(): pass\ndef baz(): pass\n"
    generated = "def bar(): pass\n"
    result = compare_regeneration(original, generated)
    assert result["api_coverage"] < 1.0
    assert "baz" in result["missing_apis"]
