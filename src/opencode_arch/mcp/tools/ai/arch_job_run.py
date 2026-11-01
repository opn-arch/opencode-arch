"""arch_job_run — execute a queued AI Job via a pluggable proposer (openAG-native).

openAG-native replacement for the AMS T16 job-run tool. Loads the repo's
proposer config, resolves the plugin, and drives one queued
:class:`~openag.ai.jobs.Job` through the state chain via
:func:`openag.ai.worker.run_job`. No ``architecture_model`` dependency.

Envelope
--------
Success: ``{"ok": True, "job": <job.to_dict()>, "proposal_ref": <str|None>}``.

When the job transitions to ``failed`` (proposer raised, returned a
non-ModelPatch, or the proposal failed validation), the tool still returns
``ok: True`` — the tool call itself succeeded — with ``proposal_ref: None``
and the job's ``error`` echoed at the envelope top level.

Errors
------
* ``INVALID_ARGUMENT`` — empty/non-str ``job_id``.
* ``NOT_FOUND`` — ``repo_path`` missing; ``details.reason`` in
  ``{"job_missing", "workorder_missing"}``.
* ``PRECONDITION_FAILED`` — ``details.reason`` in
  ``{"no_proposer_configured", "proposer_disabled",
  "proposer_config_malformed", "proposer_plugin_not_loadable",
  "proposer_plugin_not_callable", "job_not_queued"}`` (``job_not_queued``
  carries ``details.state``).
* ``INTERNAL`` — unexpected worker faults.
"""
from __future__ import annotations

import importlib

from opencode_arch.mcp._arch_tool import arch_tool

_CONFIG_REL = ".architecture/ai/proposer_config.yaml"


@arch_tool
async def arch_job_run(repo_path: str = "", job_id: str = "") -> dict:
    """Execute one queued job through the configured proposer. See module docstring."""
    import yaml

    from opencode_arch.mcp.envelope import err, ok, resolve_repo
    from openag.ai.jobs import JobState, JobStore
    from openag.ai.worker import run_job

    def _malformed(msg: str) -> dict:
        return err(
            "PRECONDITION_FAILED",
            f"proposer config malformed: {msg}",
            reason="proposer_config_malformed",
        )

    if not isinstance(job_id, str) or not job_id:
        return err("INVALID_ARGUMENT", "job_id must be a non-empty string")

    repo = resolve_repo(repo_path)

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
    try:
        final = run_job(str(repo), job_id, proposer=plugin_fn)
    except FileNotFoundError as exc:
        return err(
            "NOT_FOUND",
            f"work order YAML missing: {exc}",
            reason="workorder_missing",
        )
    except Exception as exc:  # noqa: BLE001 — surface any unexpected worker fault
        return err("INTERNAL", f"{type(exc).__name__}: {exc}")

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
    return err(
        "INTERNAL",
        f"unexpected job state after run_job: {final.state.value}",
    )


__all__ = ["arch_job_run"]
