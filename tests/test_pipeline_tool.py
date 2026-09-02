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


@pytest.mark.asyncio
async def test_cache_persistence(sample_repo):
    """Running observe, then infer uses cache for observe."""
    r1 = await run_pipeline(str(sample_repo), stage="observe")
    assert "error" not in r1, f"Pipeline error: {r1.get('error')}"

    r2 = await run_pipeline(str(sample_repo), stage="infer")
    assert "error" not in r2, f"Pipeline error: {r2.get('error')}"
    assert "observe" in r2["from_cache"]
    assert r2["stages"]["observe"]["from_cache"] is True
    assert r2["stages"]["infer"]["from_cache"] is False


@pytest.mark.asyncio
async def test_clear_cache(sample_repo):
    """clear_cache=True forces re-run."""
    r1 = await run_pipeline(str(sample_repo), stage="observe")
    assert "error" not in r1

    r2 = await run_pipeline(str(sample_repo), stage="observe", clear_cache=True)
    assert "error" not in r2
    assert r2["from_cache"] == []


@pytest.mark.asyncio
async def test_resolutions_applied(sample_repo):
    """Resolutions are converted to evidence and LLM call records."""
    resolutions = [
        {
            "category": "naming",
            "resolution": "Use 'DataProcessor' as capability name",
            "confidence": 0.9,
            "source": "llm_analysis",
            "for_stage": "infer",
            "model": "claude-sonnet-4",
            "total_tokens": 500,
        }
    ]
    result = await run_pipeline(
        str(sample_repo), stage="infer", resolutions=resolutions
    )
    assert "error" not in result, f"Pipeline error: {result.get('error')}"
    assert result["total_llm_tokens"] >= 500
    assert any(c["purpose"].startswith("resolve uncertainty") for c in result["llm_calls"])


@pytest.mark.asyncio
async def test_structured_resolutions_change_infer_and_allocation_output(sample_repo, monkeypatch):
    monkeypatch.setattr("opencode_arch.llm.relay.is_relay_available", lambda: False)
    workflow = sample_repo / "src" / "myapp" / "workflow.py"
    workflow.write_text("def run():\n    pass\n")
    resolutions = [
        {
            "category": "complex_behavior",
            "resolution": "load input -> transform record -> save result",
            "confidence": 0.9,
            "for_stage": "infer",
            "files_sent": [str(workflow.relative_to(sample_repo))],
            "target_name": "Import workflow",
            "target_kind": "behavior",
        },
        {
            "category": "ambiguous_module",
            "resolution": "Confirmed workflow boundary",
            "confidence": 0.9,
            "for_stage": "allocate",
            "files_sent": [str(workflow.relative_to(sample_repo))],
            "target_name": "Workflow Boundary",
            "target_kind": "component",
        },
    ]

    first = await run_pipeline(str(sample_repo), stage="infer", clear_cache=True)
    assert "infer" in first["from_cache"] or "infer" in first["stages_completed"]

    result = await run_pipeline(str(sample_repo), stage="allocate", resolutions=resolutions)
    assert result["stages"]["infer"]["from_cache"] is False

    from architecture_model.pipeline import PipelineCache

    infer_output = PipelineCache(
        sample_repo / ".architecture" / "pipeline-cache"
    ).load_stage("infer").output
    assert any(
        behavior.name == "Import workflow" and behavior.source_file.endswith("workflow.py")
        for behavior in infer_output.behaviors
    )
    allocation = PipelineCache(
        sample_repo / ".architecture" / "pipeline-cache"
    ).load_stage("allocate").output
    assert any(
        component.name == "Workflow Boundary" and workflow.relative_to(sample_repo) in component.files
        for component in allocation.components
    )


@pytest.mark.asyncio
async def test_uncertainties_to_resolve(sample_repo):
    """Result includes uncertainties_to_resolve from target stage."""
    result = await run_pipeline(str(sample_repo), stage="infer")
    assert "error" not in result, f"Pipeline error: {result.get('error')}"
    assert "uncertainties_to_resolve" in result
    assert isinstance(result["uncertainties_to_resolve"], list)
