"""Shared devloop helpers: proposer resolution + apply/publish.

Factored out of ``arch_work_issue`` so the author→apply→publish path can
be reused by sibling tools (``arch_learn_approve``) without importing
underscore-prefixed helpers across tool modules. These helpers carry no
logs-db/issue concerns — the issue ceremony (``_commit_and_close``,
``_existing_completed_job``, ``_build_work_order``) stays in
``arch_work_issue``.
"""
from __future__ import annotations

import hashlib
import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_PROPOSER_CONFIG_REL = ".architecture/ai/proposer_config.yaml"


class _ProposerConfigError(Exception):
    """Raised when the proposer config cannot be resolved; carries a reason."""

    def __init__(self, reason: str, message: str) -> None:
        self.reason = reason
        super().__init__(message)


@dataclass
class _ApplyResult:
    new_revision: str | None
    digest: str
    applied: bool


def _canonical_json(obj: Any) -> bytes:
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _resolve_proposer_from_config(repo: Path):
    """Load the proposer plugin from the repo's proposer config.

    Raises :class:`_ProposerConfigError` (with a ``reason``) on any fault.
    """
    import yaml

    cfg_path = repo / _PROPOSER_CONFIG_REL
    if not cfg_path.exists():
        raise _ProposerConfigError(
            "no_proposer_configured",
            "no proposer configured and none injected",
        )
    try:
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise _ProposerConfigError(
            "proposer_config_malformed", f"yaml parse error: {exc}"
        ) from exc
    if not isinstance(cfg, dict):
        raise _ProposerConfigError(
            "proposer_config_malformed", "top-level must be a mapping"
        )
    plugin = cfg.get("plugin")
    if not isinstance(plugin, str) or ":" not in plugin:
        raise _ProposerConfigError(
            "proposer_config_malformed",
            "'plugin' must be of the form 'module.path:function_name'",
        )
    module_path, _, func_name = plugin.partition(":")
    if not module_path or not func_name:
        raise _ProposerConfigError(
            "proposer_config_malformed",
            "'plugin' must be of the form 'module.path:function_name'",
        )
    try:
        module = importlib.import_module(module_path)
        fn = getattr(module, func_name)
    except (ImportError, AttributeError, ModuleNotFoundError) as exc:
        raise _ProposerConfigError(
            "proposer_plugin_not_loadable",
            f"proposer plugin not loadable: {exc}",
        ) from exc
    if not callable(fn):
        raise _ProposerConfigError(
            "proposer_plugin_not_callable",
            f"proposer plugin {plugin!r} is not callable",
        )
    return fn


def _apply_and_publish(repo: Path, proposal_data: dict, *, dry_run: bool, reason: str):
    """Apply a ModelPatch to the current model doc; publish unless ``dry_run``.

    Returns ``(_ApplyResult, None)`` on success, or ``(None, error_str)`` when
    the proposal fails validation/apply.
    """
    from openag.llm.proposal import apply_proposal, proposal_from_dict
    from openag.model_io import load_model_dir

    doc = load_model_dir(str(repo / ".architecture" / "model"))
    prop = proposal_from_dict(proposal_data, task_class="", prompt_digest="")
    try:
        new_doc = apply_proposal(doc, prop)
    except ValueError as exc:
        return None, str(exc)

    digest = "sha256:" + hashlib.sha256(_canonical_json(new_doc)).hexdigest()
    if dry_run:
        return _ApplyResult(new_revision=None, digest=digest, applied=False), None

    from openag.lifecycle.package import publish_generation

    pub = publish_generation(str(repo), new_doc, reason=reason)
    return (
        _ApplyResult(new_revision=pub["gen_id"], digest=digest, applied=True),
        None,
    )


__all__ = [
    "_ApplyResult",
    "_ProposerConfigError",
    "_PROPOSER_CONFIG_REL",
    "_apply_and_publish",
    "_canonical_json",
    "_resolve_proposer_from_config",
]
