"""Tests for adaptive token budget."""
import pytest
from opencode_arch.mcp.tools.slice import compute_adaptive_budget


class TestComputeAdaptiveBudget:
    def test_small_repo_base_budget(self):
        assert compute_adaptive_budget(5) == 4000
        assert compute_adaptive_budget(20) == 4000

    def test_medium_repo_scales(self):
        assert compute_adaptive_budget(50) == 4600
        assert compute_adaptive_budget(100) == 5600

    def test_large_repo_scales(self):
        assert compute_adaptive_budget(161) == 6800

    def test_very_large_repo_capped(self):
        assert compute_adaptive_budget(500) == 13600
        assert compute_adaptive_budget(820) == 16000
        assert compute_adaptive_budget(1000) == 16000

    def test_custom_base(self):
        assert compute_adaptive_budget(20, base=2000) == 2000
        assert compute_adaptive_budget(50, base=2000) == 2600
