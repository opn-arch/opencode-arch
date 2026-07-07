"""Tests for the regen_loop module."""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import dataclass, field

from opencode_arch.cli.regen_loop import (
    run_regen_loop,
    run_subsystem_tests,
    _build_prompt,
    _parse_pytest_summary,
)
from opencode_arch.runner.base import RunResult


# Stub for Subsystem to avoid importing architecture_model in unit tests
@dataclass
class _FakeSubsystem:
    name: str
    source_files: list = field(default_factory=list)
    test_files: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)


@dataclass
class _FakeConstant:
    name: str
    value: str
    context: str = ""


@dataclass
class _FakeContract:
    test_file: str
    test_method: str
    assertion: str
    contract_type: str = "value_equality"


@dataclass
class _FakeSignature:
    name: str
    params: list = field(default_factory=list)
    returns: str = ""
    decorators: list = field(default_factory=list)
    body_hint: str = ""


class TestParsePytestSummary:
    def test_passed_and_failed(self):
        output = "===== 3 passed, 2 failed in 0.5s ====="
        passed, failed, total = _parse_pytest_summary(output)
        assert passed == 3
        assert failed == 2
        assert total == 5

    def test_all_passed(self):
        output = "===== 5 passed in 0.3s ====="
        passed, failed, total = _parse_pytest_summary(output)
        assert passed == 5
        assert failed == 0
        assert total == 5

    def test_all_failed(self):
        output = "===== 4 failed in 0.2s ====="
        passed, failed, total = _parse_pytest_summary(output)
        assert passed == 0
        assert failed == 4
        assert total == 4

    def test_no_summary(self):
        output = "no tests were collected"
        passed, failed, total = _parse_pytest_summary(output)
        assert passed == 0
        assert failed == 0
        assert total == 0


class TestBuildPrompt:
    def test_basic_prompt(self):
        prompt, _metrics = _build_prompt(
            subsystem_name="core",
            source_files=[Path("src/core.py")],
            model_context="Component: Core",
            constants=[_FakeConstant(name="VERSION", value="1.0", context="module version")],
            signatures=[_FakeSignature(name="init", params=["self", "config"], returns="None")],
            contracts=[_FakeContract(
                test_file="test_core.py",
                test_method="test_init",
                assertion="init(config) returns None",
            )],
            dependency_apis="- Depends on 'utils'",
            iteration=1,
            max_iterations=5,
            previous_feedback="",
        )
        assert "core" in prompt
        assert "iteration 1/5" in prompt
        assert "src/core.py" in prompt
        assert "VERSION" in prompt
        assert "init(self, config)" in prompt
        assert "init(config) returns None" in prompt
        assert "Depends on 'utils'" in prompt

    def test_with_feedback(self):
        prompt, _metrics = _build_prompt(
            subsystem_name="parser",
            source_files=[],
            model_context="",
            constants=[],
            signatures=[],
            contracts=[],
            dependency_apis="",
            iteration=2,
            max_iterations=5,
            previous_feedback="- Missing symbol: Foo",
        )
        assert "iteration 2/5" in prompt
        assert "Missing symbol: Foo" in prompt
        assert "Feedback from previous iteration" in prompt

    def test_no_constants(self):
        prompt, _metrics = _build_prompt(
            subsystem_name="minimal",
            source_files=[],
            model_context="",
            constants=[],
            signatures=[],
            contracts=[],
            dependency_apis="",
            iteration=1,
            max_iterations=3,
            previous_feedback="",
        )
        assert "(none extracted)" in prompt


class TestRunSubsystemTests:
    def test_no_test_files(self):
        result = run_subsystem_tests([], Path("/tmp"))
        assert result["total"] == 0
        assert result["pass_rate"] == 0.0

    def test_nonexistent_files(self):
        result = run_subsystem_tests(
            [Path("/tmp/nonexistent_test_xyz.py")],
            Path("/tmp"),
        )
        assert result["total"] == 0

    def test_real_passing_test(self):
        """Run a simple passing test file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_simple.py"
            test_file.write_text("def test_pass():\n    assert 1 + 1 == 2\n")
            result = run_subsystem_tests([test_file], Path(tmpdir))
            assert result["passed"] == 1
            assert result["failed"] == 0
            assert result["pass_rate"] == 1.0

    def test_real_failing_test(self):
        """Run a simple failing test file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_fail.py"
            test_file.write_text("def test_fail():\n    assert False\n")
            result = run_subsystem_tests([test_file], Path(tmpdir))
            assert result["failed"] == 1
            assert result["pass_rate"] == 0.0


class TestRunRegenLoop:
    @pytest.mark.asyncio
    async def test_nonexistent_repo(self):
        """Should fail for nonexistent repo path."""
        mock_runner = AsyncMock()
        result = await run_regen_loop(
            repo_path=Path("/tmp/nonexistent_xyz_regen"),
            runner=mock_runner,
        )
        assert result.get("success") is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_no_subsystems(self):
        """Empty repo should return no subsystems error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_runner = AsyncMock()
            with patch("opencode_arch.cli.regen_loop.test_affinity_decompose", return_value=[]):
                result = await run_regen_loop(
                    repo_path=Path(tmpdir),
                    runner=mock_runner,
                )
                assert result.get("success") is False
                assert "No subsystems" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_converges_immediately(self):
        """If tests pass on first try, should converge in 1 iteration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple test that passes
            test_file = Path(tmpdir) / "test_core.py"
            test_file.write_text("def test_ok():\n    assert True\n")
            source_file = Path(tmpdir) / "core.py"
            source_file.write_text("x = 1\n")

            subsystem = _FakeSubsystem(
                name="core",
                source_files=[source_file],
                test_files=[test_file],
                dependencies=[],
            )

            mock_runner = AsyncMock()
            mock_runner.run.return_value = RunResult(output="done", exit_code=0, success=True)

            with patch("opencode_arch.cli.regen_loop.test_affinity_decompose", return_value=[subsystem]) as mock_decompose, \
                 patch("opencode_arch.cli.regen_loop.analyze_test_file") as mock_analyze, \
                 patch("opencode_arch.cli.regen_loop._record_outcome"):
                mock_analyze.return_value = MagicMock(contracts=[], constants=[], required_imports=[])

                result = await run_regen_loop(
                    repo_path=Path(tmpdir),
                    runner=mock_runner,
                    target_pass_rate=0.5,
                )
                assert result["success"] is True
                assert result["converged_subsystems"] == 1
                assert result["subsystem_results"]["core"]["converged"] is True
                assert result["subsystem_results"]["core"]["iterations"] == 1

    @pytest.mark.asyncio
    async def test_filter_by_subsystem_name(self):
        """Should only process the named subsystem."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_alpha.py"
            test_file.write_text("def test_ok():\n    assert True\n")

            sub_alpha = _FakeSubsystem(name="alpha", source_files=[], test_files=[test_file])
            sub_beta = _FakeSubsystem(name="beta", source_files=[], test_files=[])

            mock_runner = AsyncMock()
            mock_runner.run.return_value = RunResult(output="done", exit_code=0, success=True)

            with patch("opencode_arch.cli.regen_loop.test_affinity_decompose", return_value=[sub_alpha, sub_beta]), \
                 patch("opencode_arch.cli.regen_loop.analyze_test_file") as mock_analyze, \
                 patch("opencode_arch.cli.regen_loop._record_outcome"):
                mock_analyze.return_value = MagicMock(contracts=[], constants=[], required_imports=[])

                result = await run_regen_loop(
                    repo_path=Path(tmpdir),
                    runner=mock_runner,
                    subsystem_name="alpha",
                )
                assert result["success"] is True
                assert "alpha" in result["subsystem_results"]
                assert "beta" not in result["subsystem_results"]

    @pytest.mark.asyncio
    async def test_subsystem_not_found(self):
        """Should error when named subsystem doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sub = _FakeSubsystem(name="core", source_files=[], test_files=[])
            mock_runner = AsyncMock()

            with patch("opencode_arch.cli.regen_loop.test_affinity_decompose", return_value=[sub]):
                result = await run_regen_loop(
                    repo_path=Path(tmpdir),
                    runner=mock_runner,
                    subsystem_name="nonexistent",
                )
                assert result.get("success") is False
                assert "not found" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_max_iterations_exhausted(self):
        """Should stop after max_iterations even if not converged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test that always fails
            test_file = Path(tmpdir) / "test_hard.py"
            test_file.write_text("def test_fail():\n    assert False, 'always fails'\n")

            subsystem = _FakeSubsystem(
                name="hard",
                source_files=[],
                test_files=[test_file],
                dependencies=[],
            )

            mock_runner = AsyncMock()
            mock_runner.run.return_value = RunResult(output="done", exit_code=0, success=True)

            with patch("opencode_arch.cli.regen_loop.test_affinity_decompose", return_value=[subsystem]), \
                 patch("opencode_arch.cli.regen_loop.analyze_test_file") as mock_analyze, \
                 patch("opencode_arch.cli.regen_loop._record_outcome"):
                mock_analyze.return_value = MagicMock(contracts=[], constants=[], required_imports=[])

                result = await run_regen_loop(
                    repo_path=Path(tmpdir),
                    runner=mock_runner,
                    max_iterations=2,
                    target_pass_rate=0.5,
                )
                assert result["success"] is True
                assert result["subsystem_results"]["hard"]["converged"] is False
                assert result["subsystem_results"]["hard"]["iterations"] == 2
