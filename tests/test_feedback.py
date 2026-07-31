"""Tests for architect_feedback tool."""
import json
import pytest
from pathlib import Path

from opencode_arch.mcp.tools.feedback import record_feedback


@pytest.mark.asyncio
class TestRecordFeedback:
    async def test_creates_feedback_file(self, tmp_path):
        result = await record_feedback(
            str(tmp_path), "correction", "Auth should include session.py"
        )
        assert result["recorded"] is True
        assert result["feedback_id"] == "FB-1"
        assert (tmp_path / ".architecture" / "feedback.jsonl").exists()

    async def test_appends_entries(self, tmp_path):
        await record_feedback(str(tmp_path), "correction", "Fix 1")
        result = await record_feedback(str(tmp_path), "rating", "Good", rating=5)
        assert result["feedback_id"] == "FB-2"
        assert result["total_feedback"] == 2
        
        lines = (tmp_path / ".architecture" / "feedback.jsonl").read_text().splitlines()
        assert len(lines) == 2

    async def test_stores_all_fields(self, tmp_path):
        await record_feedback(
            str(tmp_path), "training", "Extract architecture",
            context={"tool": "architect_slice", "budget": 4000},
            rating=4,
            correction={"entity_id": "COMP-3", "field": "files", "new": ["auth.py"]},
        )
        line = (tmp_path / ".architecture" / "feedback.jsonl").read_text().strip()
        entry = json.loads(line)
        assert entry["type"] == "training"
        assert entry["rating"] == 4
        assert entry["context"]["tool"] == "architect_slice"
        assert entry["correction"]["entity_id"] == "COMP-3"

    async def test_rating_only(self, tmp_path):
        result = await record_feedback(
            str(tmp_path), "rating", "Good grouping", rating=5
        )
        assert result["recorded"] is True
        line = (tmp_path / ".architecture" / "feedback.jsonl").read_text().strip()
        entry = json.loads(line)
        assert entry["rating"] == 5
