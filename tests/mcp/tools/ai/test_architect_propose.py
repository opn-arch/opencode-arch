"""Task 21 — MCP architect_propose tool.

Verifies that ``architect_propose`` (Phase 4 Task 21):

* validates the ``.llm`` suffix on ``projector_name``,
* materializes the given slice against the published root package,
* dispatches the matching WriteBackProjector with a policy-resolved
  provider,
* persists the resulting proposal to
  ``.architecture/ai/proposals/<proposal_id>.yaml``,
* returns ``{ok, proposal_id, work_order_id, apply_hint}``.

Tests use a mock LLMProvider registered against a stub ``family1.mission``
base projector so no live model calls are made.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest


MODEL_YAML = """\
meta:
  project: test
  schema_version: '2.0'
entities:
  components:
    - id: COMP-A
      name: A
      status: ACTIVE
  capabilities:
    - id: CAP-1
      name: FirstCap
      status: ACTIVE
relationships:
  - from: COMP-A
    to: CAP-1
    type: realizes
"""


_POLICY_YAML = """
rules:
  MissionAuthoring:
    provider: mock
    model: mock-mission
    max_cost_usd_per_call: 0.50
    fallback: []
projector_rules:
  family1.mission.llm:
    task_class: MissionAuthoring
    max_cost_usd_per_call: 0.50
global_budget_usd: 10.0
retry_backoff: []
"""


def _run(coro):
    return asyncio.run(coro)


def _publish(repo: Path) -> None:
    from opencode_arch.mcp.tools.lifecycle.package_publish import publish_package_tool
    env = _run(publish_package_tool(repo_path=str(repo), model_yaml=MODEL_YAML))
    assert env["ok"], env


def _write_policy(repo: Path) -> None:
    (repo / ".architecture" / "llm").mkdir(parents=True, exist_ok=True)
    (repo / ".architecture" / "llm" / "policy.yaml").write_text(_POLICY_YAML)


@pytest.fixture
def stub_base_and_provider(monkeypatch):
    """Register a stub ``family1.mission`` base + mock LLM provider."""
    from architecture_model.core.diagram_spec import DiagramSpec
    from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY
    from opencode_arch.llm import registry

    def base(fragment, config):
        return DiagramSpec(
            id="prose:family1.mission",
            title="Mission",
            facets={"content_kind": "markdown", "body": "# Mission stub"},
        )

    DEFAULT_REGISTRY.register("family1.mission", base, version="1.0.0")
    registry.clear_cache()

    class _MockProvider:
        name = "mock"

        def complete(self, prompt, **kw):
            return {
                "text": "{}", "tokens_prompt": 1, "tokens_completion": 1,
                "model": "mock", "cost_usd": 0.0, "provider": "mock",
            }

        def stream(self, prompt, **kw):
            yield ""

        def structured(self, prompt, schema=None, **kw):
            # Return authored payload matching Family1MissionLLM's schema.
            return {
                "authored": [
                    {
                        "entity_id": "CAP-1",
                        "intent": "Deliver first capability.",
                        "goals": ["Ship on time", "Measure fidelity"],
                    }
                ]
            }

        def tokenize(self, text):
            return len(text.split())

    monkeypatch.setattr(registry, "get_provider", lambda name: _MockProvider())

    try:
        yield
    finally:
        try:
            DEFAULT_REGISTRY.unregister("family1.mission")
        except Exception:
            pass
        registry.clear_cache()


def _slice() -> dict:
    return {
        "id": "slice-mission",
        "architecture_id": "root-pkg",
        "model_revision": "0000001",
        "scope": "local",
        "closure": "strict",
        "shared_refs": "none",
        "selectors": {"entity_kinds": ["capability"]},
    }


@pytest.fixture
def propose():
    from opencode_arch.mcp.tools.ai.propose import architect_propose_tool
    return architect_propose_tool


def test_happy_path_writes_proposal_and_returns_envelope(
    tmp_path: Path, stub_base_and_provider, propose
) -> None:
    _publish(tmp_path)
    _write_policy(tmp_path)

    env = _run(
        propose(
            repo_path=str(tmp_path),
            projector_name="family1.mission.llm",
            slice_spec=_slice(),
        )
    )
    assert env["ok"] is True, env
    assert "proposal_id" in env
    assert env["work_order_id"].startswith("wo-")
    assert env["apply_hint"].startswith("architect_proposal_apply")
    assert env["work_order_id"] in env["apply_hint"]

    yaml_path = (
        tmp_path / ".architecture" / "ai" / "proposals" / f"{env['proposal_id']}.yaml"
    )
    assert yaml_path.exists()

    import yaml
    persisted = yaml.safe_load(yaml_path.read_text())
    assert persisted["provenance"]["proposal_id"] == env["proposal_id"]


def test_rejects_non_llm_projector_name(tmp_path: Path, propose) -> None:
    _publish(tmp_path)
    env = _run(
        propose(
            repo_path=str(tmp_path),
            projector_name="family1.mission",  # missing .llm
            slice_spec=_slice(),
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


def test_rejects_unknown_projector(
    tmp_path: Path, stub_base_and_provider, propose
) -> None:
    _publish(tmp_path)
    _write_policy(tmp_path)
    env = _run(
        propose(
            repo_path=str(tmp_path),
            projector_name="family99.mystery.llm",
            slice_spec=_slice(),
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


def test_rejects_non_dict_slice_spec(tmp_path: Path, propose) -> None:
    _publish(tmp_path)
    env = _run(
        propose(
            repo_path=str(tmp_path),
            projector_name="family1.mission.llm",
            slice_spec="not-a-dict",
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"


@pytest.mark.no_pkg_init
def test_missing_package_yields_not_found(
    tmp_path: Path, stub_base_and_provider, propose
) -> None:
    # No _publish call → package.yaml absent.
    _write_policy(tmp_path)
    env = _run(
        propose(
            repo_path=str(tmp_path),
            projector_name="family1.mission.llm",
            slice_spec=_slice(),
        )
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
