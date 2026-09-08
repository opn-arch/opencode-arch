"""MCP tool: execute a queued AI Job via a pluggable proposer (T16).

Envelope
--------
Success: ``{"ok": True, "job": <job.to_dict()>, "proposal_ref": <str|None>}``.

When the underlying job transitions to ``failed`` (proposer raised,
returned a non-Proposal, or the proposal failed validation), the tool
still returns ``ok: True`` — the tool call itself succeeded — but sets
``proposal_ref`` to ``None`` and echoes the job's ``error`` string at
the envelope top level for visibility.

Errors
------
* ``INVALID_ARGUMENT`` — empty ``job_id``.
* ``NOT_FOUND`` — ``details.reason`` is ``"repo_missing"``,
  ``"job_missing"``, or ``"workorder_missing"``.
* ``PRECONDITION_FAILED`` — ``details.reason`` is one of
  ``"no_proposer_configured"``,
  ``"proposer_disabled"``,
  ``"proposer_config_malformed"``,
  ``"proposer_plugin_not_loadable"``,
  ``"proposer_plugin_not_callable"``,
  or ``"job_not_queued"`` (with ``details.state``).
* ``INTERNAL`` — unexpected exceptions from the worker.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import yaml

from opencode_arch.mcp.envelope import err, ok, tool_result
from architecture_model.sil.decorators import instrumented

_CONFIG_REL = ".architecture/ai/proposer_config.yaml"


def _malformed(msg: str) -> dict:
    return err(
        "PRECONDITION_FAILED",
        f"proposer config malformed: {msg}",
        reason="proposer_config_malformed",
    )


@instrumented("mcp_tool:architect_job_run")
@tool_result
async def architect_job_run_tool(repo_path: str, job_id: str) -> dict:
    """Execute one queued job through the configured proposer."""
    if not isinstance(job_id, str) or not job_id:
        return err("INVALID_ARGUMENT", "job_id must be a non-empty string")

    if not isinstance(repo_path, str) or not repo_path:
        return err(
            "NOT_FOUND",
            "repo_path does not exist",
            reason="repo_missing",
        )
    repo = Path(repo_path).expanduser().resolve()
    if not repo.exists() or not repo.is_dir():
        return err(
            "NOT_FOUND",
            f"repo_path does not exist: {repo}",
            reason="repo_missing",
        )

    # ---- Load proposer config -------------------------------------------
    cfg_path = repo / _CONFIG_REL
    if not cfg_path.exists():
        return err(
            "PRECONDITION_FAILED",
            "no proposer configured",
            reason="no_proposer_configured",
            expected_path=_CONFIG_REL,
        )
    try:
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return _malformed(f"yaml parse error: {exc}")

    if not isinstance(cfg, dict):
        return _malformed("top-level must be a mapping")

    plugin_ref = cfg.get("plugin")
    if not isinstance(plugin_ref, str) or not plugin_ref:
        return _malformed("'plugin' must be a non-empty string")

    enabled = cfg.get("enabled", True)
    if enabled is False:
        return err(
            "PRECONDITION_FAILED",
            "proposer is disabled",
            reason="proposer_disabled",
        )

    # ---- Resolve plugin -------------------------------------------------
    if plugin_ref.count(":") < 1:
        return _malformed(
            "'plugin' must be of the form 'module.path:function_name'"
        )
    module_path, _, func_name = plugin_ref.partition(":")
    if not module_path or not func_name:
        return _malformed(
            "'plugin' must be of the form 'module.path:function_name'"
        )

    try:
        module = importlib.import_module(module_path)
        plugin_fn = getattr(module, func_name)
    except (ImportError, AttributeError, ModuleNotFoundError) as exc:
        return err(
            "PRECONDITION_FAILED",
            f"proposer plugin not loadable: {exc}",
            reason="proposer_plugin_not_loadable",
            detail=str(exc),
        )

    if not callable(plugin_fn):
        return err(
            "PRECONDITION_FAILED",
            f"proposer plugin {plugin_ref!r} is not callable",
            reason="proposer_plugin_not_callable",
        )

    # ---- Load & check job ----------------------------------------------
    from architecture_model.ai.jobs import JobState, JobStore

    store = JobStore(root=repo)
    try:
        job = store.get(job_id)
    except KeyError:
        return err(
            "NOT_FOUND",
            f"job {job_id!r} not found",
            reason="job_missing",
            job_id=job_id,
        )
    if job.state != JobState.queued:
        return err(
            "PRECONDITION_FAILED",
            f"job {job_id!r} is not queued (state={job.state.value})",
            reason="job_not_queued",
            state=job.state.value,
        )

    # ---- Run worker -----------------------------------------------------
    from opencode_arch.lifecycle_exec.worker import run_job

    try:
        final = run_job(
            str(repo), job_id, proposer=plugin_fn, input_slices={}
        )
    except FileNotFoundError as exc:
        return err(
            "NOT_FOUND",
            f"work order YAML missing: {exc}",
            reason="workorder_missing",
        )
    except Exception as exc:  # noqa: BLE001 — surface any unexpected worker fault
        return err(
            "INTERNAL",
            f"{type(exc).__name__}: {exc}",
        )

    # ---- Build envelope -------------------------------------------------
    job_dict = final.to_dict()
    if final.state == JobState.completed:
        return ok({"job": job_dict, "proposal_ref": final.result_ref})
    if final.state == JobState.failed:
        return ok(
            {
                "job": job_dict,
                "proposal_ref": None,
                "error": final.error or "job failed",
            }
        )
    # Unexpected terminal state (shouldn't happen).
    return err(
        "INTERNAL",
        f"unexpected job state after run_job: {final.state.value}",
    )


__all__ = ["architect_job_run_tool"]
