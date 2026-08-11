"""Tests for architect_pipeline MCP tool."""
import pytest

from opencode_arch.mcp.tools.pipeline import run_pipeline


@pytest.fixture
def sample_repo(tmp_path):
    """Create a minimal Python repo for pipeline testing."""
    src = tmp_path / "src" / "myapp"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("")
    (src / "core.py").write_text(
        "def process(data: list) -> list:\n"
        "    return [x * 2 for x in data]\n"
    )
    (src / "utils.py").write_text(
        "from myapp.core import process\n\n"
        "def run():\n"
        "    return process([1, 2, 3])\n"
    )
    return tmp_path


@pytest.mark.asyncio
async def test_run_pipeline_to_observe(sample_repo):
    """Pipeline runs observe stage and returns expected keys."""
    result = await run_pipeline(str(sample_repo), stage="observe")
    assert "error" not in result, f"Pipeline error: {result.get('error')}"
    assert "stages" in result
    assert "pipeline_report" in result
    assert "lessons" in result
    assert "artifacts_dir" in result
    assert "llm_calls" in result
    assert "total_llm_tokens" in result


@pytest.mark.asyncio
async def test_stage_summaries_have_required_fields(sample_repo):
    """Each stage summary contains score, duration_ms, diagnostics, uncertainties."""
    result = await run_pipeline(str(sample_repo), stage="infer")
    assert "error" not in result, f"Pipeline error: {result.get('error')}"
    assert len(result["stages"]) > 0
    for name, summary in result["stages"].items():
        assert "score" in summary, f"Stage {name} missing score"
        assert "duration_ms" in summary, f"Stage {name} missing duration_ms"
        assert "diagnostics" in summary, f"Stage {name} missing diagnostics"
        assert "uncertainties" in summary, f"Stage {name} missing uncertainties"


@pytest.mark.asyncio
async def test_report_and_lessons_are_strings(sample_repo):
    """Pipeline report and lessons are non-empty strings."""
    result = await run_pipeline(str(sample_repo), stage="allocate")
    assert "error" not in result, f"Pipeline error: {result.get('error')}"
    assert isinstance(result["pipeline_report"], str)
    assert len(result["pipeline_report"]) > 0
    assert isinstance(result["lessons"], str)


@pytest.mark.asyncio
async def test_run_to_specific_stage(sample_repo):
    """Running to a specific stage only runs that stage and its deps."""
    result = await run_pipeline(str(sample_repo), stage="observe")
    assert "error" not in result, f"Pipeline error: {result.get('error')}"
    assert "observe" in result["stages"]


@pytest.mark.asyncio
async def test_nonexistent_repo():
    """Non-existent repo returns error."""
    result = await run_pipeline("/nonexistent/path/12345")
    assert "error" in result


@pytest.mark.asyncio
async def test_llm_calls_list(sample_repo):
    """LLM calls is a list and total_llm_tokens is an int."""
    result = await run_pipeline(str(sample_repo), stage="observe")
    assert "error" not in result, f"Pipeline error: {result.get('error')}"
    assert isinstance(result["llm_calls"], list)
    assert isinstance(result["total_llm_tokens"], int)
