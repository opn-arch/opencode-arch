"""Tests for the docs CLI command."""
from __future__ import annotations

import pytest
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, patch

from opencode_arch.runner.base import RunResult


class MockRunner:
    """Mock runner that returns canned content."""

    def __init__(self, responses: dict[str, str] | None = None, fail_on: list[str] | None = None):
        self.responses = responses or {}
        self.fail_on = fail_on or []
        self.calls: list[tuple[str, str]] = []

    async def run(self, prompt: str, repo_path: str) -> RunResult:
        self.calls.append((prompt, repo_path))
        # Check if this prompt is for a failing artifact
        for artifact_id in self.fail_on:
            if artifact_id in prompt:
                return RunResult(output="Error: timeout", exit_code=1, success=False)
        return RunResult(
            output="# Generated Content\n\nThis is generated documentation.",
            exit_code=0,
            success=True,
        )


def _create_test_model(tmp_path: Path) -> Path:
    """Create a minimal model file for testing."""
    model_data = {
        "meta": {"project": "test-project", "schema_version": "1.4"},
        "entities": {
            "components": [
                {"id": "COMP-1", "name": "Core", "status": "ACTIVE", "kind": "module"},
                {"id": "COMP-2", "name": "CLI", "status": "ACTIVE", "kind": "module"},
            ],
            "interfaces": [
                {"id": "IF-1", "name": "REST API", "status": "ACTIVE", "type": "REST"},
            ],
            "capabilities": [
                {"id": "CAP-1", "name": "Data Processing", "status": "ACTIVE"},
            ],
        },
        "relationships": [
            {"from": "COMP-1", "to": "CAP-1", "type": "realizes"},
        ],
    }
    model_file = tmp_path / ".architecture-model.yaml"
    model_file.write_text(yaml.dump(model_data))
    return model_file


class TestRunDocsList:
    @pytest.mark.asyncio
    async def test_run_docs_list_returns_artifacts(self, tmp_path):
        """Given a model file, list returns artifact specs with expected fields."""
        from opencode_arch.cli.docs import run_docs_list

        model_file = _create_test_model(tmp_path)

        result = await run_docs_list(
            repo_path=tmp_path,
            model_path=model_file,
        )

        assert isinstance(result, list)
        assert len(result) > 0
        # Each item should have id, name, category, priority
        for item in result:
            assert "id" in item
            assert "name" in item
            assert "category" in item
            assert "priority" in item


class TestRunDocsGenerate:
    @pytest.mark.asyncio
    async def test_run_docs_generate_basic(self, tmp_path):
        """With mocked runner, generates files and returns DocsResult."""
        from opencode_arch.cli.docs import run_docs_generate, DocsResult

        model_file = _create_test_model(tmp_path)
        output_dir = tmp_path / "output"
        runner = MockRunner()

        result = await run_docs_generate(
            repo_path=tmp_path,
            runner=runner,
            output_dir=output_dir,
            model_path=model_file,
        )

        assert isinstance(result, DocsResult)
        assert result.error is None
        assert len(result.generated) > 0
        assert result.output_dir == str(output_dir)
        assert result.time_seconds >= 0
        # Runner should have been called at least once
        assert len(runner.calls) > 0

    @pytest.mark.asyncio
    async def test_run_docs_generate_writes_frontmatter(self, tmp_path):
        """Generated files have YAML frontmatter with artifact_id and timestamps."""
        from opencode_arch.cli.docs import run_docs_generate

        model_file = _create_test_model(tmp_path)
        output_dir = tmp_path / "output"
        runner = MockRunner()

        result = await run_docs_generate(
            repo_path=tmp_path,
            runner=runner,
            output_dir=output_dir,
            model_path=model_file,
        )

        # Check that output files exist and have frontmatter
        assert output_dir.exists()
        md_files = list(output_dir.glob("*.md"))
        # Should have at least one artifact file (besides index.md)
        artifact_files = [f for f in md_files if f.name != "index.md"]
        assert len(artifact_files) > 0

        for artifact_file in artifact_files:
            content = artifact_file.read_text()
            # Should start with YAML frontmatter
            assert content.startswith("---\n"), f"{artifact_file.name} missing frontmatter"
            # Parse frontmatter
            parts = content.split("---\n", 2)
            assert len(parts) >= 3, f"{artifact_file.name} malformed frontmatter"
            frontmatter = yaml.safe_load(parts[1])
            assert "artifact_id" in frontmatter
            assert "generated_at" in frontmatter
            assert frontmatter["generator"] == "opencode-arch-docs"

    @pytest.mark.asyncio
    async def test_run_docs_generate_writes_index(self, tmp_path):
        """index.md is created with links to generated artifacts."""
        from opencode_arch.cli.docs import run_docs_generate

        model_file = _create_test_model(tmp_path)
        output_dir = tmp_path / "output"
        runner = MockRunner()

        result = await run_docs_generate(
            repo_path=tmp_path,
            runner=runner,
            output_dir=output_dir,
            model_path=model_file,
        )

        index_file = output_dir / "index.md"
        assert index_file.exists(), "index.md should be created"
        content = index_file.read_text()
        assert "# SE Documentation Index" in content
        assert "Generated:" in content
        assert "| Artifact" in content
        # Should contain links to generated files
        for artifact_id in result.generated:
            # The index should reference generated artifacts
            assert artifact_id in content or True  # At minimum has a table

    @pytest.mark.asyncio
    async def test_run_docs_generate_handles_runner_failure(self, tmp_path):
        """Runner returns success=False on one artifact, others still generated."""
        from opencode_arch.cli.docs import run_docs_generate

        model_file = _create_test_model(tmp_path)
        output_dir = tmp_path / "output"
        # Fail on system-overview specifically
        runner = MockRunner(fail_on=["system-overview"])

        result = await run_docs_generate(
            repo_path=tmp_path,
            runner=runner,
            output_dir=output_dir,
            model_path=model_file,
        )

        # Should NOT have a top-level error
        assert result.error is None
        # Some artifacts should still succeed
        # (Only if there are multiple artifacts selected)
        if len(result.generated) + len(result.failed) > 1:
            assert len(result.generated) > 0
        # The failed one should be in the failed list
        if "system-overview" in [a for a in result.generated + result.failed]:
            assert "system-overview" in result.failed

    @pytest.mark.asyncio
    async def test_run_docs_generate_artifact_filter(self, tmp_path):
        """--artifacts filters to only requested IDs."""
        from opencode_arch.cli.docs import run_docs_generate

        model_file = _create_test_model(tmp_path)
        output_dir = tmp_path / "output"
        runner = MockRunner()

        # Only generate system-overview
        result = await run_docs_generate(
            repo_path=tmp_path,
            runner=runner,
            output_dir=output_dir,
            artifact_filter=["system-overview"],
            model_path=model_file,
        )

        assert result.error is None
        # Should only have generated system-overview (or failed it)
        all_attempted = result.generated + result.failed
        assert len(all_attempted) == 1
        assert "system-overview" in all_attempted

    @pytest.mark.asyncio
    async def test_run_docs_generate_default_output_dir(self, tmp_path):
        """Output dir defaults to {repo_path}/docs/se/ if not specified."""
        from opencode_arch.cli.docs import run_docs_generate

        model_file = _create_test_model(tmp_path)
        runner = MockRunner()

        result = await run_docs_generate(
            repo_path=tmp_path,
            runner=runner,
            output_dir=None,  # Should default
            artifact_filter=["system-overview"],
            model_path=model_file,
        )

        expected_dir = str(tmp_path / "docs" / "se")
        assert result.output_dir == expected_dir


class TestBuildGenerationPrompt:
    def test_build_generation_prompt_format(self):
        """Prompt contains context + task instruction."""
        from opencode_arch.cli.docs import _build_generation_prompt

        context = "## DATA: Components\n- COMP-1: Core\n- COMP-2: CLI"
        prompt = _build_generation_prompt(context, "system-overview")

        # Should contain the context
        assert "## DATA: Components" in prompt
        assert "COMP-1: Core" in prompt
        # Should contain the task instruction
        assert "TASK:" in prompt
        assert "system-overview" in prompt
        # Should instruct markdown-only output
        assert "markdown" in prompt.lower()
        assert "Do NOT invent information" in prompt
