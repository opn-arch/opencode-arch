"""B1.2.6 — verify OpencodeRunner.run_via_policy routes through Policy.pick().complete()."""

from pathlib import Path
import pytest


def test_run_via_policy_uses_stub_provider(tmp_path, monkeypatch):
    # 1. Write policy.yaml selecting a task class → "stub" provider.
    (tmp_path / ".architecture" / "llm").mkdir(parents=True)
    (tmp_path / ".architecture" / "llm" / "policy.yaml").write_text(
        "rules:\n"
        "  extract:\n"
        "    provider: stub\n"
        "    model: stub-model\n"
        "    max_cost_usd_per_call: 0.10\n"
        "    fallback: []\n"
        "global_budget_usd: 10.0\n"
        "retry_backoff: [0.0]\n"
    )

    # 2. Register a stub in the LLM registry.
    from opencode_arch.llm import registry
    calls = []

    class _Stub:
        name = "stub"
        def complete(self, prompt, **kw):
            calls.append(prompt)
            return {"text": "stub-output", "tokens_prompt": 1,
                    "tokens_completion": 1, "model": "stub-model",
                    "finish_reason": "stop"}
        def stream(self, prompt, **kw): yield "stub-output"
        def structured(self, prompt, schema, **kw): return {}
        def tokenize(self, t): return len(t.split())

    registry.clear_cache()
    registry._CACHE["stub"] = _Stub()

    # 3. Runner.run_via_policy delegates to stub — NOT subprocess.
    from opencode_arch.runner.opencode import OpencodeRunner
    runner = OpencodeRunner()
    result = runner.run_via_policy("say hi", task_class_name="extract", repo_path=str(tmp_path))

    assert result.success
    assert result.output == "stub-output"
    assert calls == ["say hi"]

    registry.clear_cache()


def test_run_via_policy_falls_back_to_subprocess_when_no_policy(tmp_path, monkeypatch):
    """No policy.yaml → run_via_policy invokes existing run() (subprocess path).

    We assert this by monkeypatching OpencodeRunner.run to a coroutine returning a sentinel.
    """
    from opencode_arch.runner.opencode import OpencodeRunner
    from opencode_arch.runner.base import RunResult

    async def _fake_run(self, prompt, repo_path):
        return RunResult(output="fake-subproc-output", exit_code=0, success=True)

    monkeypatch.setattr(OpencodeRunner, "run", _fake_run)
    result = OpencodeRunner().run_via_policy("x", task_class_name="anything", repo_path=str(tmp_path))
    assert result.output == "fake-subproc-output"
