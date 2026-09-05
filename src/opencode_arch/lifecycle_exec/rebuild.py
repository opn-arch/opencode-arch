"""Artifact rebuild executor (T11).

Executes a list of ArtifactSpec contracts (non-zip only for T11): resolves
each spec's view + slice from parallel input lists, materializes the
slice, projects the view, renders bytes via the registered renderer, and
atomically writes to ``<repo>/.architecture/lifecycle/artifacts/<id>.<ext>``.

Deviations from the plan doc (see T11 amendment)
------------------------------------------------
* ``spec.expected_digest`` doesn't exist as a field on Phase 1
  :class:`ArtifactSpec` (``extra="forbid"``). We read the expected
  digest from ``spec.parameters["expected_digest"]`` instead. Callers
  wanting a skip/mismatch decision must plumb the digest through the
  spec's free-form ``parameters`` dict.
* The plan suggested ``get_renderer(view.output_content_kind or ...)``.
  ``ViewSpec.output_content_kind`` is one of ``diagram``/``prose``/
  ``table`` — not a renderer name. We use ``spec.renderer`` (matching
  T9's ``view_render`` behavior).
* Phase 1's :func:`materialize` requires an ``ArchitecturePackage``, not
  a bare slice. We resolve the package from
  ``<repo>/.architecture/lifecycle/package.yaml`` (rebased via
  ``resolve_current_pkg``) and pass it in.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Renderer → extension map
# ---------------------------------------------------------------------------
_EXT: dict[str, str] = {
    "svg": "svg",
    "markdown": "md",
    "html": "html",
    "ai-context": "txt",
}


@dataclass
class RebuildReport:
    built: list[dict] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    failed: list[dict] = field(default_factory=list)
    journal_events: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "built": list(self.built),
            "skipped": list(self.skipped),
            "failed": list(self.failed),
            "journal_events": list(self.journal_events),
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_repo(repo_path: str | Path) -> Path:
    if repo_path is None:
        raise ValueError("repo_path must not be None")
    p = Path(repo_path).expanduser().resolve()
    if not p.exists() or not p.is_dir():
        raise ValueError(f"repo_path does not exist or is not a directory: {p}")
    return p


def _load_pkg(repo: Path):
    """Load and current-generation-rebase the root architecture package.

    Returns None if the package is not published; callers should surface
    materialize_error for each artifact needing it.
    """
    from architecture_model.lifecycle.package import load_package

    from opencode_arch.lifecycle_bridge import resolve_current_pkg

    from opencode_arch.lifecycle_exec import paths as _paths

    tree = _paths.ensure_all(repo)
    lifecycle_root: Path = tree["package_root"]
    if not (lifecycle_root / "package.yaml").exists():
        return None
    return resolve_current_pkg(load_package(lifecycle_root))


def _journal(
    kind: str,
    spec_id: str,
    ts: str,
    *,
    output_path: str | None = None,
    emitted_digest: str | None = None,
    reason: str | None = None,
) -> dict:
    return {
        "kind": kind,
        "spec_id": spec_id,
        "timestamp": ts,
        "output_path": output_path,
        "emitted_digest": emitted_digest,
        "reason": reason,
    }


def _parse_error(report: RebuildReport, detail: str) -> RebuildReport:
    report.failed.append({
        "spec_id": "*",
        "reason": "spec_parse_error",
        "detail": detail,
    })
    return report


def _dag_error(report: RebuildReport, detail: str) -> RebuildReport:
    report.failed.append({
        "spec_id": "*",
        "reason": "dag_error",
        "detail": detail,
    })
    return report


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def rebuild_artifacts(
    repo_path: str | Path,
    artifact_specs: list[dict],
    view_specs: list[dict],
    slice_specs: list[dict],
    *,
    force: bool = False,
    _now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> RebuildReport:
    """Rebuild a set of artifacts. See module docstring for details."""
    from pydantic import ValidationError

    from architecture_model.lifecycle.artifact_dag import (
        ArtifactDAGCycle,
        MissingArtifactRef,
        build_artifact_dag,
    )
    from architecture_model.lifecycle.artifact_spec import ArtifactSpec
    from architecture_model.lifecycle.atomic_store import write_atomic
    from architecture_model.lifecycle.model_slice import ModelSlice
    from architecture_model.lifecycle.model_slice_materializer import materialize
    from architecture_model.lifecycle.renderers import get_renderer
    from architecture_model.lifecycle.view_projection import project
    from architecture_model.lifecycle.view_spec import ViewSpec

    from opencode_arch.lifecycle_exec import paths as _paths

    repo = _resolve_repo(repo_path)
    report = RebuildReport()

    # 1. Parse artifact specs.
    if not artifact_specs:
        return _parse_error(report, "artifact_specs must be a non-empty list")
    artifacts: list[ArtifactSpec] = []
    for i, raw in enumerate(artifact_specs):
        if not isinstance(raw, dict):
            return _parse_error(
                report, f"artifact_specs[{i}] must be a mapping, got {type(raw).__name__}"
            )
        try:
            artifacts.append(ArtifactSpec(**raw))
        except (ValidationError, TypeError, ValueError) as exc:
            return _parse_error(report, f"artifact_specs[{i}]: {exc}")

    # 2. Parse view specs.
    views: list[ViewSpec] = []
    for i, raw in enumerate(view_specs or []):
        if not isinstance(raw, dict):
            return _parse_error(
                report, f"view_specs[{i}] must be a mapping, got {type(raw).__name__}"
            )
        try:
            views.append(ViewSpec(**raw))
        except (ValidationError, TypeError, ValueError) as exc:
            return _parse_error(report, f"view_specs[{i}]: {exc}")

    slices: list[ModelSlice] = []
    for i, raw in enumerate(slice_specs or []):
        if not isinstance(raw, dict):
            return _parse_error(
                report, f"slice_specs[{i}] must be a mapping, got {type(raw).__name__}"
            )
        try:
            slices.append(ModelSlice(**raw))
        except (ValidationError, TypeError, ValueError) as exc:
            return _parse_error(report, f"slice_specs[{i}]: {exc}")

    # 3. Build DAG.
    try:
        dag = build_artifact_dag(artifacts)
        order = dag.topological_order()
    except (ArtifactDAGCycle, MissingArtifactRef) as exc:
        return _dag_error(report, str(exc))

    # 4. Build lookups; detect duplicates.
    views_by_key: dict[tuple[str, str], ViewSpec] = {}
    for v in views:
        key = (v.id, v.slice_ref.model_revision)
        if key in views_by_key:
            return _dag_error(
                report,
                f"duplicate view (view_id={v.id!r}, model_revision={v.slice_ref.model_revision!r})",
            )
        views_by_key[key] = v
    slices_by_key: dict[tuple[str, str], ModelSlice] = {
        (s.id, s.model_revision): s for s in slices
    }

    artifacts_by_id = {a.id: a for a in artifacts}

    # 5. Ensure output directory exists.
    out_dir: Path = _paths.artifact_dir(repo)

    # Load the architecture package once (lazy — some tests never trigger materialize).
    pkg = None
    pkg_load_error: str | None = None
    try:
        pkg = _load_pkg(repo)
        if pkg is None:
            pkg_load_error = "package.yaml not found — publish a package first"
    except Exception as exc:  # pragma: no cover — defensive
        pkg_load_error = f"load_package failed: {exc}"

    # 6. Process each artifact in topological order.
    for spec_id in order:
        spec = artifacts_by_id[spec_id]
        ts = _now().isoformat()

        # -- zip renderer -----------------------------------------------------
        if spec.renderer == "zip":
            report.failed.append({
                "spec_id": spec_id,
                "reason": "zip_renderer_unsupported",
                "detail": "T11 does not execute zip renderers",
            })
            report.journal_events.append(
                _journal("artifact.failed", spec_id, ts, reason="zip_renderer_unsupported")
            )
            continue

        # -- resolve view -----------------------------------------------------
        vkey = (spec.view_ref.view_id, spec.view_ref.model_revision)
        view = views_by_key.get(vkey)
        if view is None:
            report.failed.append({
                "spec_id": spec_id,
                "reason": "unresolved_view_ref",
                "detail": f"no ViewSpec matches (view_id={vkey[0]!r}, model_revision={vkey[1]!r})",
            })
            report.journal_events.append(
                _journal("artifact.failed", spec_id, ts, reason="unresolved_view_ref")
            )
            continue

        # -- resolve slice ----------------------------------------------------
        skey = (view.slice_ref.slice_id, view.slice_ref.model_revision)
        slice_obj = slices_by_key.get(skey)
        if slice_obj is None:
            report.failed.append({
                "spec_id": spec_id,
                "reason": "unresolved_slice_ref",
                "detail": f"no ModelSlice matches (slice_id={skey[0]!r}, model_revision={skey[1]!r})",
            })
            report.journal_events.append(
                _journal("artifact.failed", spec_id, ts, reason="unresolved_slice_ref")
            )
            continue

        # -- federated slice --------------------------------------------------
        if slice_obj.scope == "federated":
            report.failed.append({
                "spec_id": spec_id,
                "reason": "federated_slice_unsupported",
                "detail": "federated slices require a registry resolver (deferred)",
            })
            report.journal_events.append(
                _journal("artifact.failed", spec_id, ts, reason="federated_slice_unsupported")
            )
            continue

        # -- materialize ------------------------------------------------------
        if pkg is None:
            report.failed.append({
                "spec_id": spec_id,
                "reason": "materialize_error",
                "detail": pkg_load_error or "no package loaded",
            })
            report.journal_events.append(
                _journal("artifact.failed", spec_id, ts, reason="materialize_error")
            )
            continue
        try:
            ms = materialize(slice_obj, pkg)
        except Exception as exc:  # noqa: BLE001
            report.failed.append({
                "spec_id": spec_id,
                "reason": "materialize_error",
                "detail": str(exc),
            })
            report.journal_events.append(
                _journal("artifact.failed", spec_id, ts, reason="materialize_error")
            )
            continue

        # -- project ----------------------------------------------------------
        try:
            pv = project(view, ms)
        except Exception as exc:  # noqa: BLE001
            report.failed.append({
                "spec_id": spec_id,
                "reason": "project_error",
                "detail": str(exc),
            })
            report.journal_events.append(
                _journal("artifact.failed", spec_id, ts, reason="project_error")
            )
            continue

        # -- render -----------------------------------------------------------
        renderer_name = spec.renderer  # See deviations note in module docstring.
        try:
            renderer = get_renderer(renderer_name)
        except KeyError as exc:
            report.failed.append({
                "spec_id": spec_id,
                "reason": "render_error",
                "detail": f"renderer not registered: {exc}",
            })
            report.journal_events.append(
                _journal("artifact.failed", spec_id, ts, reason="render_error")
            )
            continue

        try:
            result = renderer(pv, spec)
        except Exception as exc:  # noqa: BLE001
            report.failed.append({
                "spec_id": spec_id,
                "reason": "render_error",
                "detail": str(exc),
            })
            report.journal_events.append(
                _journal("artifact.failed", spec_id, ts, reason="render_error")
            )
            continue

        # Renderer contract: registered renderers return bytes. Accept a few
        # tolerant shapes so a future ProjectedView-style return still works.
        if isinstance(result, (bytes, bytearray)):
            body: bytes = bytes(result)
        elif hasattr(result, "body") and isinstance(result.body, (bytes, bytearray)):
            body = bytes(result.body)
        elif hasattr(result, "body_utf8") and isinstance(result.body_utf8, str):
            body = result.body_utf8.encode("utf-8")
        else:
            report.failed.append({
                "spec_id": spec_id,
                "reason": "render_error",
                "detail": f"renderer returned unsupported type {type(result).__name__}",
            })
            report.journal_events.append(
                _journal("artifact.failed", spec_id, ts, reason="render_error")
            )
            continue

        emitted_digest = "sha256:" + hashlib.sha256(body).hexdigest()

        # -- output path ------------------------------------------------------
        ext = _EXT.get(renderer_name)
        if ext is None:
            report.failed.append({
                "spec_id": spec_id,
                "reason": "render_error",
                "detail": f"no extension mapping for renderer {renderer_name!r}",
            })
            report.journal_events.append(
                _journal("artifact.failed", spec_id, ts, reason="render_error")
            )
            continue

        output_path = out_dir / f"{spec_id}.{ext}"

        expected = None
        if isinstance(spec.parameters, dict):
            expected = spec.parameters.get("expected_digest")

        # -- skip check -------------------------------------------------------
        if (
            output_path.exists()
            and not force
            and expected is not None
            and expected == emitted_digest
        ):
            report.skipped.append({
                "spec_id": spec_id,
                "output_path": str(output_path),
                "reason": "up_to_date",
            })
            report.journal_events.append(
                _journal(
                    "artifact.skipped",
                    spec_id,
                    ts,
                    output_path=str(output_path),
                    emitted_digest=emitted_digest,
                    reason="up_to_date",
                )
            )
            continue

        # -- digest mismatch --------------------------------------------------
        if expected is not None and expected != emitted_digest:
            pending = output_path.with_name(output_path.name + ".pending")
            try:
                write_atomic(pending, body)
            except Exception as exc:  # noqa: BLE001
                report.failed.append({
                    "spec_id": spec_id,
                    "reason": "write_error",
                    "detail": f"failed to write pending: {exc}",
                })
                report.journal_events.append(
                    _journal("artifact.failed", spec_id, ts, reason="write_error")
                )
                continue
            report.failed.append({
                "spec_id": spec_id,
                "reason": "digest_mismatch",
                "detail": f"expected={expected} got={emitted_digest}",
                "output_path": str(pending),
            })
            report.journal_events.append(
                _journal(
                    "artifact.failed",
                    spec_id,
                    ts,
                    output_path=str(pending),
                    emitted_digest=emitted_digest,
                    reason="digest_mismatch",
                )
            )
            continue

        # -- write ------------------------------------------------------------
        try:
            write_atomic(output_path, body)
        except Exception as exc:  # noqa: BLE001
            report.failed.append({
                "spec_id": spec_id,
                "reason": "write_error",
                "detail": str(exc),
            })
            report.journal_events.append(
                _journal("artifact.failed", spec_id, ts, reason="write_error")
            )
            continue

        report.built.append({
            "spec_id": spec_id,
            "output_path": str(output_path),
            "emitted_digest": emitted_digest,
            "renderer": renderer_name,
        })
        report.journal_events.append(
            _journal(
                "artifact.built",
                spec_id,
                ts,
                output_path=str(output_path),
                emitted_digest=emitted_digest,
            )
        )

    return report


__all__ = ["RebuildReport", "rebuild_artifacts"]
