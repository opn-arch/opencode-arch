"""MCP tool: three-way merge of three published generations (T20).

Loads three revisions from the repo's root ``ArchitecturePackage``,
delegates to :func:`opencode_arch.lifecycle_exec.merge.three_way_merge`,
and — when the merge is conflict-free — publishes the merged model as
a new generation and records a ``lifecycle.package.merge`` journal
event. When conflicts are present, no new generation is published and
the merger's structured conflict list is returned to the caller.

Envelope
--------
Success (no conflicts): ``{"ok": True, "merged_digest": <str>,
"conflicts": [], "stats": {...}, "merged_revision": "<7-digit>"}``.

Success but conflicts present: ``{"ok": True, "merged_digest": None,
"conflicts": [<conflict dicts>], "stats": {...}}``. The tool returns
``ok=True`` because the tool ran successfully — the caller must inspect
``conflicts`` and either resolve them or refuse. This mirrors the
envelope convention: transport-level failures alone map to ``ok=False``.

Errors
------
* ``SCHEMA_VIOLATION`` — revision string does not match ``^\\d{7}$``.
* ``NOT_FOUND`` — repo missing; no ``package.yaml``; any of the three
  named revisions is absent from the package. ``details.reason`` names
  which revision.
* ``PRECONDITION_FAILED`` — one of the revisions is malformed and its
  model file will not parse. ``details.reason`` includes the revision.
* ``INTERNAL`` — ``MergeIntegrityError`` (bug in merger placeholder
  heuristic) or any other unexpected exception (no stack leaked).
"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import Any

from opencode_arch.lifecycle_exec import paths
from opencode_arch.lifecycle_exec.merge import (
    Conflict,
    MergeIntegrityError,
    three_way_merge,
)
from opencode_arch.mcp.envelope import err, ok, resolve_repo, tool_result

_REV_RE = re.compile(r"^\d{7}$")
_MODEL_REL = Path("model") / ".architecture-model.yaml"
_MANIFEST_REL = Path("manifest") / "manifest.json"


def _json_safe(value: Any) -> Any:
    """Recursively coerce Path → str for JSON serialization."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _conflict_dict(c: Conflict) -> dict:
    d = dataclasses.asdict(c)
    return _json_safe(d)


@tool_result
async def architect_package_merge_tool(
    repo_path: str,
    base_revision: str,
    local_revision: str,
    remote_revision: str,
) -> dict:
    """Three-way merge base/local/remote revisions into a new generation."""
    # Lazy Phase 1 imports.
    from architecture_model.core.parser import load_model
    from architecture_model.lifecycle.journal import Journal
    from architecture_model.lifecycle.package import load_package
    from architecture_model.lifecycle.publication import (
        PackageBundle,
        _generation_dir,
        list_generations,
        publish,
    )

    # 1. Validate revision format.
    for label, rev in (
        ("base", base_revision),
        ("local", local_revision),
        ("remote", remote_revision),
    ):
        if not isinstance(rev, str) or not _REV_RE.match(rev):
            return err(
                "SCHEMA_VIOLATION",
                "revision must be 7-digit zero-padded generation id",
                reason=f"{label}_revision_invalid",
                revision=rev,
            )

    # 2. Resolve repo + package.
    repo = resolve_repo(repo_path)
    tree = paths.ensure_all(repo)
    lifecycle_root = tree["package_root"]

    pkg_yaml = lifecycle_root / "package.yaml"
    if not pkg_yaml.exists():
        return err(
            "NOT_FOUND",
            f"no package at {pkg_yaml}",
            reason="package_missing",
        )

    pkg = load_package(lifecycle_root)
    gens = list_generations(pkg)

    labels = {
        "base": base_revision,
        "local": local_revision,
        "remote": remote_revision,
    }
    for label, rev in labels.items():
        if int(rev) not in gens:
            return err(
                "NOT_FOUND",
                f"generation {rev} not found",
                reason=f"{label}_revision_missing",
                revision=rev,
            )

    # 3. Load the three models.
    loaded: dict[str, Any] = {}
    for label, rev in labels.items():
        gen_dir = _generation_dir(pkg, int(rev))
        model_path = gen_dir / _MODEL_REL
        try:
            loaded[label] = load_model(model_path)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:  # noqa: BLE001
            return err(
                "PRECONDITION_FAILED",
                f"revision {rev} model is malformed",
                reason=f"revision {rev} model is malformed",
                revision=rev,
                cause=f"{type(exc).__name__}: {exc}".splitlines()[0],
            )

    # 4. Delegate to the merger.
    try:
        result = globals()["three_way_merge"](
            loaded["base"], loaded["local"], loaded["remote"]
        )
    except MergeIntegrityError as exc:
        return err(
            "INTERNAL",
            "merge integrity error",
            reason=f"{type(exc).__name__}: {exc}".splitlines()[0],
        )
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as exc:  # noqa: BLE001
        return err(
            "INTERNAL", f"{type(exc).__name__}: {exc}".splitlines()[0]
        )

    stats = dict(result.stats)

    # 5. Conflicts present → do not publish, no journal event.
    if result.conflicts:
        return ok({
            "merged_digest": None,
            "conflicts": [_conflict_dict(c) for c in result.conflicts],
            "stats": stats,
        })

    # 6. Publish merged model as a new generation.
    merged_yaml = result.merged_model.to_yaml()
    # Preserve manifest bytes from the local revision.
    local_gen_dir = _generation_dir(pkg, int(local_revision))
    manifest_path = local_gen_dir / _MANIFEST_REL
    manifest_bytes = (
        manifest_path.read_bytes() if manifest_path.is_file() else b""
    )
    journal_path = paths.journal_path(repo)

    try:
        pub_result = globals()["publish"](
            pkg,
            PackageBundle(
                model_bytes=merged_yaml.encode("utf-8"),
                manifest_bytes=manifest_bytes,
            ),
            journal_path=journal_path,
        )
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as exc:  # noqa: BLE001
        return err(
            "INTERNAL", f"{type(exc).__name__}: {exc}".splitlines()[0]
        )

    merged_revision = f"{pub_result.generation:07d}"
    merged_digest = pub_result.root_digest

    # 7. Journal event.
    try:
        Journal(journal_path).record(
            event="lifecycle.package.merge",
            payload={
                "base_revision": base_revision,
                "local_revision": local_revision,
                "remote_revision": remote_revision,
                "merged_revision": merged_revision,
                "merged_digest": merged_digest,
                "stats": stats,
            },
        )
    except Exception as exc:  # noqa: BLE001
        return err(
            "INTERNAL",
            f"journal record failed: {type(exc).__name__}: {exc}".splitlines()[0],
        )

    return ok({
        "merged_digest": merged_digest,
        "merged_revision": merged_revision,
        "conflicts": [],
        "stats": stats,
    })


# Module-level rebind so tests can monkeypatch the ``publish`` seam via
# ``globals()`` lookup above (mirrors the T18 apply.py pattern).
from architecture_model.lifecycle.publication import publish  # noqa: E402


__all__ = ["architect_package_merge_tool"]
