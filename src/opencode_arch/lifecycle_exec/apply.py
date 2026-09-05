"""Proposal apply runner (T18).

Applies a parsed :class:`Proposal` to a repository's lifecycle store.

Public API
----------
:func:`apply_proposal` — dispatches on ``proposal.kind`` to a per-kind
applier. Returns an :class:`ApplyReport` describing what was (or would
be) written and the journal events that were (or would be) recorded.

Per-kind semantics
------------------
* ``model-patch`` — applies JSON-patch-style ops to the currently
  published root model, then publishes a new generation via
  :func:`architecture_model.lifecycle.publication.publish`. Ops are
  applied against the ``entities`` collections; supported ops are
  ``remove``, ``replace``, and ``add``. ``move`` is accepted by the
  Phase 1 validator but not implemented here (no-op with a change entry
  reflecting the op).
* ``decomposition-proposal`` — creates a child package directory (with
  ``package.yaml``) per proposed system under the lifecycle root, adds
  the child slugs to the parent's ``children`` list, and republishes
  the parent as a new generation. Child model/manifest files are NOT
  created; the child ``package.yaml`` only declares the layout.
* ``slice-proposal`` — persists the slice spec to
  ``.architecture/lifecycle/slices/<slice_id>.yaml``.
* ``view-curation-proposal`` — persists the view spec to
  ``.architecture/lifecycle/views/<view_id>.yaml``.
* ``artifact-candidate`` — persists the artifact spec to
  ``.architecture/lifecycle/artifacts_specs/<spec_id>.yaml``
  (T18 spec convention; distinct from the ``artifact_specs`` path
  used by ``paths.artifact_spec_dir`` — see deviation note below).
* ``impact-assessment`` — read-only. Emits a ``…impact_assessment_noop``
  event and returns empty ``changes``.

Drift check
-----------
For ``model-patch`` and ``decomposition-proposal`` we compare
``proposal.provenance.model_version`` against BOTH the currently
published root digest (from ``CURRENT/digest.json``) AND the padded
generation string (e.g. ``"0000001"``). If it matches neither, we
raise :class:`DriftError`.

``dry_run``
-----------
When ``dry_run=True`` (the default), no files are written, no
publication happens, and :meth:`Journal.record` is NOT called. The
``changes`` and ``journal_events`` lists are populated as a preview.
``new_revision`` / ``digest`` remain ``None``.

Deviations from the plan
------------------------
* The plan spec named the artifact-spec output directory
  ``.architecture/lifecycle/artifacts_specs/`` (with a trailing ``s``
  on ``artifact``). ``opencode_arch.lifecycle_exec.paths.artifact_spec_dir``
  uses ``artifact_specs`` instead. We follow the T18 spec exactly and
  hard-code the path.
* Phase 1 exposes no model-patch applier; T18 implements a minimal one
  in :func:`_apply_ops`. Op payload shape supported:
  ``{"op": ..., "target_id": ..., "collection"?, "value"?}``.
* ``proposal.provenance`` uses field name ``model_version`` (not
  ``model_revision``) — we compare that against both the digest and
  the padded generation string.
"""
from __future__ import annotations

import json
import re
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Module-level re-export of publish so tests can monkeypatch it and so both
# per-kind appliers share a single mockable seam.
from architecture_model.lifecycle.publication import PackageBundle, publish

# Safe id pattern: alphanumerics, dot, underscore, hyphen. No slashes, no dots
# alone, no traversal. Applied to slice/view/artifact ids and decomposition
# child slugs — any value that becomes a path segment.
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _validate_safe_id(value: Any, field_name: str) -> None:
    """Reject values that would escape their intended directory.

    Raises :class:`InvalidProposalError` if ``value`` is empty, not a str,
    equals ``.`` / ``..``, contains a path separator, or otherwise fails
    the ``[A-Za-z0-9._-]+`` whitelist.
    """
    if not isinstance(value, str) or not value:
        raise InvalidProposalError(
            f"invalid {field_name}: must be a non-empty string"
        )
    if value in {".", ".."}:
        raise InvalidProposalError(
            f"invalid {field_name}: {value!r} is not a safe id"
        )
    if "/" in value or "\\" in value:
        raise InvalidProposalError(
            f"invalid {field_name}: {value!r} contains a path separator"
        )
    if not _SAFE_ID_RE.match(value):
        raise InvalidProposalError(
            f"invalid {field_name}: {value!r} does not match ^[A-Za-z0-9._-]+$"
        )

# ---------------------------------------------------------------------------
# Public dataclass + errors
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ApplyReport:
    changes: list[dict] = field(default_factory=list)
    new_revision: str | None = None
    digest: str | None = None
    journal_events: list[dict] = field(default_factory=list)


class DriftError(RuntimeError):
    """Raised when the proposal was authored against a different revision."""

    def __init__(self, *, expected: str | None, actual: str | None) -> None:
        super().__init__(
            f"model drift: expected={expected!r} actual={actual!r}"
        )
        self.expected = expected
        self.actual = actual


class InvalidProposalError(ValueError):
    """Raised when the proposal dict cannot be parsed into a Proposal."""


class PackageNotFoundError(RuntimeError):
    """Raised when the repo's root lifecycle package.yaml is missing."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _lifecycle_root(repo: Path) -> Path:
    return repo / ".architecture" / "lifecycle"


def _journal_path(repo: Path) -> Path:
    return _lifecycle_root(repo) / "journal.jsonl"


def _to_proposal(proposal: Any):
    """Coerce ``proposal`` to a concrete Proposal dataclass."""
    from architecture_model.ai.proposals import (
        ArtifactCandidate,
        DecompositionProposal,
        ImpactAssessment,
        ModelPatch,
        SliceProposal,
        ViewCurationProposal,
        proposal_from_dict,
    )

    _proposal_types = (
        ModelPatch,
        DecompositionProposal,
        SliceProposal,
        ViewCurationProposal,
        ArtifactCandidate,
        ImpactAssessment,
    )
    if isinstance(proposal, _proposal_types):
        return proposal
    if isinstance(proposal, dict):
        try:
            return proposal_from_dict(proposal)
        except (KeyError, ValueError, TypeError) as exc:
            raise InvalidProposalError(str(exc)) from exc
    raise InvalidProposalError(
        f"unsupported proposal type: {type(proposal).__name__}"
    )


def _load_root_pkg(repo: Path):
    from architecture_model.lifecycle.package import load_package

    lifecycle_root = _lifecycle_root(repo)
    if not (lifecycle_root / "package.yaml").exists():
        raise PackageNotFoundError(
            f"package.yaml not found at {lifecycle_root}"
        )
    return load_package(lifecycle_root)


def _current_state(pkg) -> tuple[str | None, str | None]:
    """Return (current_root_digest, current_revision) or (None, None)."""
    from architecture_model.lifecycle.publication import read_current_generation

    gen = read_current_generation(pkg)
    if gen is None:
        return None, None
    revision = f"{gen:07d}"
    digest_path = pkg.root / "CURRENT" / "digest.json"
    digest: str | None = None
    if digest_path.exists():
        try:
            data = json.loads(digest_path.read_text(encoding="utf-8"))
            digest = data.get("root_digest")
        except (json.JSONDecodeError, OSError):
            digest = None
    return digest, revision


def _drift_check(proposal, pkg) -> None:
    expected = proposal.provenance.model_version
    actual_digest, actual_rev = _current_state(pkg)
    if expected in {actual_digest, actual_rev}:
        return
    raise DriftError(expected=expected, actual=actual_digest or actual_rev)


def _proposal_id(proposal) -> str:
    return getattr(proposal.provenance, "work_order_id", "unknown")


def _record_journal(repo: Path, events: list[dict]) -> None:
    from architecture_model.lifecycle.journal import Journal

    journal = Journal(_journal_path(repo))
    for ev in events:
        journal.record(event=ev["event"], payload=ev["payload"])


# ---------------------------------------------------------------------------
# Model-patch op applier
# ---------------------------------------------------------------------------


def _apply_ops(model_data: dict, operations: list[dict]) -> dict:
    """Apply a minimal JSON-patch-like op list to a parsed model dict.

    Supported op shapes::

        {"op": "remove",  "target_id": "<id>"}
        {"op": "replace", "target_id": "<id>", "value": {<field>: <value>}}
        {"op": "add",     "collection": "components",
         "value": {"id": "<id>", ...}}

    Note (N52): ``architecture_model.ai.apply_model_patch`` is the public
    helper for applying a ``ModelPatch`` to an ``ArchitectureModel``. We
    intentionally do NOT delegate to it here because the contracts diverge:

    * data shape — this runner mutates the raw YAML dict in place; the
      public helper operates on a parsed ``ArchitectureModel`` dataclass.
    * missing-target semantics — this runner raises
      :class:`InvalidProposalError` when a ``remove``/``replace`` target
      is not found; the public helper is a silent no-op.
    * ``add`` payload — this runner uses ``collection`` and rejects
      duplicate ids; the public helper uses ``target_kind`` and re-parses
      the value through ``_parse_raw`` without deduplication.
    * ``replace`` payload — this runner merges a dict via
      ``entity.update(value)``; the public helper expects a ``field``
      key and applies ``setattr(entity, field, value)``.
    * error type — ``InvalidProposalError`` vs ``ParseError``.

    Adopting the public helper would either change externally-observable
    error contracts that tests depend on or require a compat shim thicker
    than this inline implementation.
    """
    entities = model_data.get("entities")
    if entities is None:
        entities = {}
        model_data["entities"] = entities

    def _find(target_id: str) -> tuple[str | None, int | None]:
        for coll, items in entities.items():
            if not isinstance(items, list):
                continue
            for idx, item in enumerate(items):
                if isinstance(item, dict) and item.get("id") == target_id:
                    return coll, idx
        return None, None

    for op in operations:
        if not isinstance(op, dict):
            raise InvalidProposalError(f"invalid op (not a dict): {op!r}")
        kind = op.get("op")
        target = op.get("target_id")
        value = op.get("value")
        if kind == "remove":
            if target is None:
                raise InvalidProposalError("remove op missing target_id")
            coll, idx = _find(target)
            if coll is None or idx is None:
                raise InvalidProposalError(
                    f"target_id {target!r} not found in model"
                )
            del entities[coll][idx]
        elif kind == "replace":
            if target is None:
                raise InvalidProposalError("replace op missing target_id")
            if not isinstance(value, dict):
                raise InvalidProposalError(
                    "replace op requires dict 'value'"
                )
            coll, idx = _find(target)
            if coll is None or idx is None:
                raise InvalidProposalError(
                    f"target_id {target!r} not found in model"
                )
            entities[coll][idx].update(value)
        elif kind == "add":
            coll = op.get("collection") or "components"
            entry = dict(value or {})
            if target is not None and "id" not in entry:
                entry["id"] = target
            new_id = entry.get("id")
            if new_id is not None:
                existing_coll, existing_idx = _find(new_id)
                if existing_coll is not None:
                    raise InvalidProposalError(
                        f"duplicate id {new_id!r} in add op"
                    )
            entities.setdefault(coll, [])
            entities[coll].append(entry)
        elif kind == "move":
            raise InvalidProposalError(
                "move op not yet supported by apply runner"
            )
        else:
            raise InvalidProposalError(f"unsupported op kind: {kind!r}")
    return model_data


# ---------------------------------------------------------------------------
# Per-kind appliers
# ---------------------------------------------------------------------------


def _apply_model_patch(repo: Path, proposal, dry_run: bool) -> ApplyReport:
    from opencode_arch.lifecycle_bridge import resolve_current_pkg

    pkg = _load_root_pkg(repo)
    _drift_check(proposal, pkg)

    cur_pkg = resolve_current_pkg(pkg)
    model_path = cur_pkg.root / cur_pkg.model_ref
    model_data = yaml.safe_load(model_path.read_text(encoding="utf-8")) or {}
    _apply_ops(model_data, list(proposal.operations))

    changes: list[dict] = [
        {"op": op.get("op"), "target_id": op.get("target_id")}
        for op in proposal.operations
        if isinstance(op, dict)
    ]

    new_revision: str | None = None
    digest: str | None = None
    if not dry_run:
        new_bytes = yaml.safe_dump(
            model_data, sort_keys=True, default_flow_style=False
        ).encode("utf-8")
        manifest_path = cur_pkg.root / cur_pkg.manifest_ref
        manifest_bytes = (
            manifest_path.read_bytes() if manifest_path.exists() else b""
        )
        result = globals()["publish"](
            pkg,
            PackageBundle(model_bytes=new_bytes, manifest_bytes=manifest_bytes),
            journal_path=_journal_path(repo),
        )
        new_revision = f"{result.generation:07d}"
        digest = result.root_digest

    events = [
        {
            "event": "ai.proposal.apply.model_patch",
            "payload": {
                "proposal_id": _proposal_id(proposal),
                "new_revision": new_revision,
                "digest": digest,
            },
        }
    ]
    if not dry_run:
        _record_journal(repo, events)
    return ApplyReport(
        changes=changes,
        new_revision=new_revision,
        digest=digest,
        journal_events=events,
    )


def _apply_decomposition(repo: Path, proposal, dry_run: bool) -> ApplyReport:
    from architecture_model.lifecycle.versions import SchemaVersions

    from opencode_arch.lifecycle_bridge import resolve_current_pkg

    pkg = _load_root_pkg(repo)
    _drift_check(proposal, pkg)

    lifecycle_root = _lifecycle_root(repo)
    child_slugs: list[str] = []
    changes: list[dict] = []
    for sys in proposal.proposed_systems:
        if not isinstance(sys, dict):
            continue
        slug = sys.get("id") if "id" in sys else sys.get("slug")
        # C1: validate before ever touching the filesystem.
        _validate_safe_id(slug, "decomposition child slug")
        child_slugs.append(slug)
        changes.append({"child_slug": slug, "name": sys.get("name")})

    # C2: detect duplicates within the proposal AND against parent's existing children.
    parent_path = lifecycle_root / "package.yaml"
    parent_data = yaml.safe_load(parent_path.read_text(encoding="utf-8")) or {}
    existing_children = list(parent_data.get("children") or [])
    seen: set[str] = set()
    for slug in child_slugs:
        if slug in seen:
            raise InvalidProposalError(
                f"duplicate child slug in proposal: {slug!r}"
            )
        seen.add(slug)
        if slug in existing_children:
            raise InvalidProposalError(
                f"child slug already exists in parent: {slug!r}"
            )

    new_revision: str | None = None
    digest: str | None = None
    parent_id = pkg.architecture_id

    if not dry_run:
        # C2: stage-then-commit ordering.
        #   1. Build updated parent bundle in memory (no disk writes yet).
        #   2. Stage child package.yaml files under a temp dir.
        #   3. publish() the parent — Phase 1's atomic commit point.
        #   4. On success: rename staged children into place, then rewrite
        #      the parent package.yaml on disk.
        #   On any failure between (2) and (4): rmtree staging, leave the
        #   parent package.yaml UNCHANGED, do not create new generation.
        from architecture_model.lifecycle.publication import (
            PackageBundle,
        )
        # Use module-level `publish` so tests can monkeypatch this seam.
        _publish = globals()["publish"]

        staging_dir = lifecycle_root / f".staging-{uuid.uuid4().hex}"
        try:
            staging_dir.mkdir(parents=True, exist_ok=False)
            for slug in child_slugs:
                child_stage = staging_dir / slug
                child_stage.mkdir(parents=True, exist_ok=False)
                (child_stage / "package.yaml").write_text(
                    yaml.safe_dump(
                        {
                            "architecture_id": slug,
                            "name": slug,
                            "slug": slug,
                            "contract_version": SchemaVersions.PACKAGE,
                            "model_ref": "model/.architecture-model.yaml",
                            "manifest_ref": "manifest/manifest.json",
                        },
                        sort_keys=True,
                        default_flow_style=False,
                    ),
                    encoding="utf-8",
                )

            # Build in-memory updated parent (not yet on disk).
            updated_parent = dict(parent_data)
            updated_parent["children"] = existing_children + list(child_slugs)

            # Preserve current model + manifest bytes for republish.
            cur = resolve_current_pkg(pkg)
            model_bytes = (cur.root / cur.model_ref).read_bytes()
            manifest_path = cur.root / cur.manifest_ref
            manifest_bytes = (
                manifest_path.read_bytes()
                if manifest_path.exists()
                else b""
            )

            # Commit point: publish. Parent package.yaml is STILL unchanged
            # on disk at this moment.
            result = _publish(
                pkg,
                PackageBundle(
                    model_bytes=model_bytes, manifest_bytes=manifest_bytes
                ),
                journal_path=_journal_path(repo),
            )

            # Publish succeeded: rename staged children into final locations.
            import os

            for slug in child_slugs:
                src = staging_dir / slug
                dst = lifecycle_root / slug
                os.replace(src, dst)

            # Rewrite parent package.yaml AFTER publish + child rename.
            parent_path.write_text(
                yaml.safe_dump(
                    updated_parent,
                    sort_keys=True,
                    default_flow_style=False,
                ),
                encoding="utf-8",
            )

            new_revision = f"{result.generation:07d}"
            digest = result.root_digest
            # architecture_id is preserved from parent pkg.
            parent_id = pkg.architecture_id
        finally:
            # Always clean up the staging dir (empty on success after
            # os.replace, or contains leftovers on failure).
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)

    events = [
        {
            "event": "ai.proposal.apply.decomposition",
            "payload": {
                "proposal_id": _proposal_id(proposal),
                "parent_id": parent_id,
                "children": list(child_slugs),
                "new_revision": new_revision,
            },
        }
    ]
    if not dry_run:
        _record_journal(repo, events)
    return ApplyReport(
        changes=changes,
        new_revision=new_revision,
        digest=digest,
        journal_events=events,
    )


def _apply_file_spec(
    repo: Path,
    proposal,
    *,
    dry_run: bool,
    subdir: str,
    spec: dict,
    id_field: str,
    event: str,
    payload_id_key: str,
) -> ApplyReport:
    if "id" in spec:
        spec_id = spec["id"]
    elif id_field in spec:
        spec_id = spec[id_field]
    else:
        spec_id = "unknown"
    _validate_safe_id(spec_id, f"{payload_id_key}")
    target = _lifecycle_root(repo) / subdir / f"{spec_id}.yaml"
    changes = [{payload_id_key: spec_id, "path": str(target)}]
    events = [
        {
            "event": event,
            "payload": {
                "proposal_id": _proposal_id(proposal),
                payload_id_key: spec_id,
                "path": str(target),
            },
        }
    ]
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            yaml.safe_dump(spec, sort_keys=True, default_flow_style=False),
            encoding="utf-8",
        )
        _record_journal(repo, events)
    return ApplyReport(
        changes=changes,
        new_revision=None,
        digest=None,
        journal_events=events,
    )


def _apply_impact_assessment(
    repo: Path, proposal, dry_run: bool
) -> ApplyReport:
    events = [
        {
            "event": "ai.proposal.apply.impact_assessment_noop",
            "payload": {"proposal_id": _proposal_id(proposal)},
        }
    ]
    if not dry_run:
        _record_journal(repo, events)
    return ApplyReport(
        changes=[],
        new_revision=None,
        digest=None,
        journal_events=events,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def apply_proposal(
    repo_path: str | Path,
    proposal: Any,
    *,
    dry_run: bool = True,
) -> ApplyReport:
    """Apply a proposal to the repo's lifecycle store.

    See module docstring for per-kind semantics, drift-check rules, and
    ``dry_run`` behavior.
    """
    from architecture_model.ai.proposals import (
        ArtifactCandidate,
        DecompositionProposal,
        ImpactAssessment,
        ModelPatch,
        SliceProposal,
        ViewCurationProposal,
    )

    repo = Path(repo_path).expanduser().resolve()
    parsed = _to_proposal(proposal)

    if isinstance(parsed, ImpactAssessment):
        return _apply_impact_assessment(repo, parsed, dry_run)
    if isinstance(parsed, ModelPatch):
        return _apply_model_patch(repo, parsed, dry_run)
    if isinstance(parsed, DecompositionProposal):
        return _apply_decomposition(repo, parsed, dry_run)
    if isinstance(parsed, SliceProposal):
        return _apply_file_spec(
            repo,
            parsed,
            dry_run=dry_run,
            subdir="slices",
            spec=dict(parsed.slice),
            id_field="slice_id",
            event="ai.proposal.apply.slice_persisted",
            payload_id_key="slice_id",
        )
    if isinstance(parsed, ViewCurationProposal):
        return _apply_file_spec(
            repo,
            parsed,
            dry_run=dry_run,
            subdir="views",
            spec=dict(parsed.view_spec),
            id_field="view_id",
            event="ai.proposal.apply.view_persisted",
            payload_id_key="view_id",
        )
    if isinstance(parsed, ArtifactCandidate):
        return _apply_file_spec(
            repo,
            parsed,
            dry_run=dry_run,
            subdir="artifacts_specs",
            spec=dict(parsed.artifact_spec),
            id_field="spec_id",
            event="ai.proposal.apply.artifact_spec_persisted",
            payload_id_key="spec_id",
        )

    raise InvalidProposalError(
        f"unsupported proposal kind: {type(parsed).__name__}"
    )


__all__ = [
    "ApplyReport",
    "DriftError",
    "InvalidProposalError",
    "PackageNotFoundError",
    "apply_proposal",
]
