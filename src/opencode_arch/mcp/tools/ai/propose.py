"""MCP tool: architect_propose — invoke a write-back projector.

Envelope
--------
Success::

    {
        "ok": True,
        "proposal_id": "<sha-derived>",
        "work_order_id": "wo-<uuid>",
        "apply_hint": "architect_proposal_apply repo_path=<repo> work_order_id=<wo>",
    }

Errors
------
* ``INVALID_ARGUMENT`` — ``projector_name`` does not end with ``.llm`` or
  ``slice_spec`` is not a dict.
* ``NOT_FOUND`` — ``repo_path`` missing, ``package.yaml`` absent, or
  ``projector_name`` is not a registered write-back variant.
* ``SCHEMA_VIOLATION`` — ``slice_spec`` failed :class:`ModelSlice`
  parsing.
* ``PRECONDITION_FAILED`` — policy has no rule for the resolved
  ``task_class`` or projector-side base view is missing.
* ``INTERNAL`` — the projector did not return a ``proposal`` facet or
  the proposal lacks ``provenance.proposal_id``.

Persistence
-----------
On success the proposal is written to
``<repo>/.architecture/ai/proposals/<proposal_id>.yaml`` via
:func:`architecture_model.lifecycle.atomic_store.write_atomic`.
"""
from __future__ import annotations

import uuid
from typing import Any

import yaml

from architecture_model.sil.decorators import instrumented
from opencode_arch.lifecycle_exec import paths
from opencode_arch.mcp.envelope import err, ok, resolve_repo, tool_result


_WRITE_BACK_VARIANTS: dict[str, type] = {}


def _load_write_back_variants() -> dict[str, type]:
    """Build the projector_name → class map lazily from write_back_variants."""
    global _WRITE_BACK_VARIANTS
    if _WRITE_BACK_VARIANTS:
        return _WRITE_BACK_VARIANTS
    from architecture_model.lifecycle.projectors import write_back_variants as wbv

    result: dict[str, type] = {}
    for cls_name in getattr(wbv, "__all__", ()):
        cls = getattr(wbv, cls_name, None)
        if cls is None:
            continue
        projector_name = getattr(cls, "projector_name", None)
        if projector_name:
            result[projector_name] = cls
    _WRITE_BACK_VARIANTS = result
    return result


@instrumented("mcp_tool:architect_propose")
@tool_result
async def architect_propose_tool(
    repo_path: str,
    projector_name: str,
    slice_spec: dict,
) -> dict:
    """Invoke a write-back projector; return a Proposal envelope."""
    # 1. Validate projector_name.
    if not isinstance(projector_name, str) or not projector_name.endswith(".llm"):
        return err(
            "INVALID_ARGUMENT",
            "projector_name must be a string ending with '.llm'",
        )
    variants = _load_write_back_variants()
    if projector_name not in variants:
        return err(
            "NOT_FOUND",
            f"unknown write-back projector: {projector_name}",
            projector_name=projector_name,
        )

    if not isinstance(slice_spec, dict):
        return err("INVALID_ARGUMENT", "slice_spec must be a dict")

    # 2. Resolve repo + locate root package.
    repo = resolve_repo(repo_path)
    tree = paths.ensure_all(repo)
    lifecycle_root = tree["package_root"]
    pkg_yaml = lifecycle_root / "package.yaml"
    if not pkg_yaml.exists():
        return err("NOT_FOUND", "package.yaml not found")

    from architecture_model.lifecycle.atomic_store import write_atomic
    from architecture_model.lifecycle.model_slice import ModelSlice
    from architecture_model.lifecycle.model_slice_materializer import materialize
    from architecture_model.lifecycle.package import load_package
    from opencode_arch.lifecycle_bridge import resolve_current_pkg

    pkg = resolve_current_pkg(load_package(lifecycle_root))

    # 3. Parse + materialize slice.
    try:
        slice_obj = ModelSlice(**slice_spec)
    except Exception as exc:  # noqa: BLE001 - broad by design; envelope-safe
        return err("SCHEMA_VIOLATION", "invalid slice spec", detail=str(exc))

    try:
        ms = materialize(slice_obj, pkg)
    except FileNotFoundError:
        return err("NOT_FOUND", "package model not found")

    # 4. Resolve provider via policy.
    from opencode_arch.llm.policy import TaskClass, load_policy

    try:
        policy = load_policy(repo)
    except FileNotFoundError:
        return err("PRECONDITION_FAILED", "policy.yaml not found")

    resolved = policy.resolve_projector(projector_name)
    task_class = resolved.task_class if resolved else "GenericAuthoring"
    if TaskClass(task_class) not in policy.rules:
        return err(
            "PRECONDITION_FAILED",
            f"no policy rule for task_class {task_class!r}",
            task_class=task_class,
        )
    provider = policy.pick(TaskClass(task_class))

    # 5. Instantiate the write-back projector and run it.
    wo_id = f"wo-{uuid.uuid4().hex[:12]}"
    cls = variants[projector_name]
    projector = cls(provider=provider, task_class=task_class)
    config: dict[str, Any] = {
        "__work_order_id": wo_id,
        "__model_revision": ms.model_revision,
    }
    try:
        diagram_spec = projector(ms.model_fragment, config)
    except KeyError as exc:
        # Missing base projector — surface as precondition failure.
        return err(
            "PRECONDITION_FAILED",
            f"base projector unavailable: {exc}",
            projector_name=projector_name,
        )

    proposal_dict = diagram_spec.facets.get("proposal")
    if not isinstance(proposal_dict, dict):
        return err(
            "INTERNAL",
            "projector did not return a 'proposal' facet",
            projector_name=projector_name,
        )
    provenance = proposal_dict.get("provenance") or {}
    proposal_id = provenance.get("proposal_id")
    if not proposal_id:
        return err(
            "INTERNAL",
            "proposal missing provenance.proposal_id",
            projector_name=projector_name,
        )

    # 6. Persist proposal atomically.
    proposals_dir = repo / ".architecture" / "ai" / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    target = proposals_dir / f"{proposal_id}.yaml"
    text = yaml.safe_dump(
        proposal_dict,
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
    )
    write_atomic(target, text.encode("utf-8"))

    return ok(
        {
            "proposal_id": proposal_id,
            "work_order_id": wo_id,
            "apply_hint": (
                f"architect_proposal_apply repo_path={repo_path} "
                f"work_order_id={wo_id}"
            ),
        }
    )


__all__ = ["architect_propose_tool"]
