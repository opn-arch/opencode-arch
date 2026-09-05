"""MCP tool: semantic diff between two generations of an architecture package.

Loads two published generations from the repo's root
``ArchitecturePackage`` (per Phase 1's one-root-package-per-repo layout)
and returns a serialized :class:`SemanticDiff`.

Deviation notes vs. the plan
----------------------------
* Revision format is strictly 7-digit zero-padded (``^\\d{7}$``). Unlike
  :mod:`package_load` (which accepts short forms), diff requires the
  fully-padded form because the tool is expected to be driven by IDs
  emitted from other lifecycle tools that already zero-pad.
* Manifest input to :func:`semantic_diff` is either a parsed JSON dict
  or ``None``; the empty-bytes sentinel established for
  ``manifest/manifest.json`` (see commit ``3d20e35``) collapses to
  ``None`` here — matching the behavior of ``package_load_tool``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from opencode_arch.lifecycle_exec import paths
from opencode_arch.mcp.envelope import err, ok, resolve_repo, tool_result

_REV_RE = re.compile(r"^\d{7}$")
_MODEL_REL = Path("model") / ".architecture-model.yaml"
_MANIFEST_REL = Path("manifest") / "manifest.json"


def _load_generation(pkg, gen_dir: Path):
    """Return (ArchitectureModel, manifest_dict_or_None) for a generation dir."""
    from architecture_model.core.parser import load_model

    model = load_model(gen_dir / _MODEL_REL)

    manifest = None
    manifest_path = gen_dir / _MANIFEST_REL
    if manifest_path.is_file():
        raw = manifest_path.read_bytes()
        if raw != b"":
            manifest = json.loads(raw.decode("utf-8"))
    return model, manifest


@tool_result
async def package_diff_tool(
    repo_path: str,
    from_revision: str,
    to_revision: str,
) -> dict:
    """Compute a semantic diff between two published generations."""
    from architecture_model.lifecycle.diff import semantic_diff
    from architecture_model.lifecycle.package import load_package
    from architecture_model.lifecycle.publication import (
        _generation_dir,
        list_generations,
    )

    repo = resolve_repo(repo_path)
    tree = paths.ensure_all(repo)
    lifecycle_root = tree["package_root"]

    pkg_yaml = lifecycle_root / "package.yaml"
    if not pkg_yaml.exists():
        return err("NOT_FOUND", f"no package at {pkg_yaml}")

    pkg = load_package(lifecycle_root)
    gens = list_generations(pkg)

    resolved: dict[str, int] = {}
    for label, rev in (("from", from_revision), ("to", to_revision)):
        if not isinstance(rev, str) or not _REV_RE.match(rev):
            return err(
                "INVALID_ARGUMENT",
                "revision must be 7-digit zero-padded generation id",
                revision=rev,
            )
        n = int(rev)
        if n not in gens:
            return err("NOT_FOUND", "generation not found", revision=rev)
        resolved[label] = n

    model_from, manifest_from = _load_generation(
        pkg, _generation_dir(pkg, resolved["from"])
    )
    model_to, manifest_to = _load_generation(
        pkg, _generation_dir(pkg, resolved["to"])
    )

    diff = semantic_diff(
        a=model_from,
        b=model_to,
        manifest_a=manifest_from,
        manifest_b=manifest_to,
    )

    return ok({
        "from_revision": from_revision,
        "to_revision": to_revision,
        "diff": diff.model_dump(mode="json"),
    })
