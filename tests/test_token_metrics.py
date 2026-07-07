"""Tests for token instrumentation and learning curve tracking."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def test_build_prompt_returns_metrics(tmp_path):
    """_build_prompt should return (prompt_str, PromptMetrics)."""
    from opencode_arch.cli.regen_loop import _build_prompt, PromptMetrics

    result = _build_prompt(
        subsystem_name="test_sub",
        source_files=[Path("src/foo.py")],
        model_context="# Model context here\nComponents: 5",
        constants=[],
        signatures=[],
        contracts=[],
        dependency_apis="#### Module: utils\n  def helper() -> str",
        iteration=1,
        max_iterations=3,
        previous_feedback="",
        source_equivalent_tokens=5000,
    )

    assert isinstance(result, tuple)
    prompt_str, metrics = result
    assert isinstance(prompt_str, str)
    assert isinstance(metrics, PromptMetrics)
    assert metrics.total_tokens > 0
    assert metrics.model_context_tokens > 0
    assert metrics.dependency_tokens > 0
    assert metrics.source_equivalent_tokens == 5000
    assert metrics.compression_ratio > 0


def test_prompt_metrics_compression_ratio():
    """Compression ratio = source_equivalent / total."""
    from opencode_arch.cli.regen_loop import PromptMetrics

    metrics = PromptMetrics(
        total_tokens=1000,
        model_context_tokens=200,
        signatures_tokens=300,
        constants_tokens=100,
        contracts_tokens=300,
        dependency_tokens=50,
        feedback_tokens=50,
        source_equivalent_tokens=10000,
        compression_ratio=10.0,
    )
    assert metrics.compression_ratio == 10.0


def test_learning_curve_store(tmp_path):
    """Learning curve records should be queryable and ordered."""
    from opencode_arch.telemetry.store import TelemetryStore

    store = TelemetryStore(db_path=tmp_path / "test.db")

    # Record three repos in sequence
    for i, (repo, rate) in enumerate([("colorama", 1.0), ("structlog", 0.62), ("tqdm", 0.70)]):
        store.record_learning_curve(
            repo=repo,
            mode="blind",
            total_subsystems=10,
            converged_subsystems=int(10 * rate),
            avg_pass_rate=rate,
            avg_iterations=1.5 - i * 0.2,  # should decrease
            avg_prompt_tokens=3000 - i * 500,  # should decrease
            avg_source_equivalent=20000,
            avg_compression_ratio=6.0 + i,  # should increase
            total_time_seconds=100.0,
        )

    curve = store.get_learning_curve(mode="blind")
    assert len(curve) == 3
    assert curve[0]["repo"] == "colorama"
    assert curve[0]["repo_sequence"] == 1
    assert curve[1]["repo_sequence"] == 2
    assert curve[2]["repo_sequence"] == 3
    # Verify trend: iterations should decrease
    assert curve[2]["avg_iterations"] < curve[0]["avg_iterations"]


def test_regen_outcome_with_tokens(tmp_path):
    """Regen outcomes should store token metrics."""
    from opencode_arch.telemetry.store import TelemetryStore

    store = TelemetryStore(db_path=tmp_path / "test.db")
    store.log_regen_outcome(
        repo="structlog",
        subsystem="stdlib",
        iteration=1,
        features={"constant_count": 5, "signature_count": 20, "contract_count": 50},
        pass_rate=1.0,
        time_seconds=45.0,
        prompt_tokens=8000,
        source_equivalent_tokens=41000,
        compression_ratio=5.1,
        mode="blind",
    )

    outcomes = store.query_regen_outcomes(repo="structlog")
    assert len(outcomes) >= 1
    latest = outcomes[0]
    assert latest["prompt_tokens"] == 8000
    assert latest["source_equivalent_tokens"] == 41000
    assert abs(latest["compression_ratio"] - 5.1) < 0.01
    assert latest["mode"] == "blind"


def test_compute_source_equivalent(tmp_path):
    """Source equivalent should sum target + dependency file sizes."""
    from opencode_arch.cli.regen_loop import _compute_source_equivalent

    # Create mock source files
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("x" * 4000)  # 1000 tokens
    (src / "utils.py").write_text("x" * 8000)  # 2000 tokens

    # Create mock subsystem
    sub = MagicMock()
    sub.source_files = [src / "main.py"]
    sub.dependencies = ["utils"]

    # Create mock dependency subsystem
    dep_sub = MagicMock()
    dep_sub.name = "utils"
    dep_sub.source_files = [src / "utils.py"]

    all_subs = [sub, dep_sub]

    result = _compute_source_equivalent(sub, tmp_path, all_subs)
    # main.py (4000/4=1000) + utils.py (8000/4=2000) = 3000
    assert result == 3000
