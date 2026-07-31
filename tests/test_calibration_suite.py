"""Tests for calibration suite functions."""
from opencode_arch.cli.calibrate import (
    select_calibration_targets,
    compute_correlation,
    CalibrationReport,
)


def test_select_calibration_targets_picks_diverse_confidence():
    components = [{"id": f"C{i}", "confidence": i * 0.1} for i in range(7)]
    result = select_calibration_targets(components, count=4)
    assert len(result) == 4
    # Should span low to high
    confs = [c["confidence"] for c in result]
    assert confs[0] <= 0.1  # lowest
    assert confs[-1] >= 0.5  # highest


def test_compute_correlation():
    # Perfect positive correlation
    data = [{"confidence": i, "regen_quality": i} for i in range(10)]
    r = compute_correlation(data)
    assert r > 0.9

    # Empty data
    assert compute_correlation([]) == 0.0
    assert compute_correlation([{"confidence": 1, "regen_quality": 1}]) == 0.0


def test_calibration_report_dataclass():
    report = CalibrationReport(
        components_tested=6,
        correlation=0.85,
        bands={"low": 0.3, "high": 0.9},
        threshold=0.7,
    )
    assert report.components_tested == 6
    assert report.correlation == 0.85
