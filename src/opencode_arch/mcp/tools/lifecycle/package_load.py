"""MCP tool: load an architecture package generation.

Reads the root ``package.yaml`` at ``<repo>/.architecture/lifecycle/`` and
returns the model YAML, optional manifest JSON, and root digest for the
requested generation (or the current one if ``revision`` is None).

Deviation notes vs. the plan
----------------------------
* ``root_digest`` at load time is read from ``<gen_dir>/digest.json``
  (Phase 1's ``publish()`` writes this canonical-JSON document containing
  ``root_digest``). No on-the-fly recomputation is needed.
* Generation layout is dictated by Phase 1's ``publish()``:
    - ``model/.architecture-model.yaml``
    - ``manifest/manifest.json``
    - ``digest.json``
* A published-without-manifest bundle is stored as a 0-byte
  ``manifest/manifest.json`` file (see T4 ``package_publish``). We
  treat empty bytes (size 0) as "no manifest" and return
  ``manifest_json: None``. This is unambiguous with a legitimate
  ``'{}'`` payload (2 bytes), which round-trips exactly.
* Short-form revisions (e.g. ``"1"``) are accepted as long as they match
  ``^\\d{1,7}$``; anything else -> ``INVALID_ARGUMENT``.
* If no root ``package.yaml`` exists, this tool does NOT auto-create one
  (unlike publish). Callers must publish first.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from opencode_arch.lifecycle_exec import paths
from opencode_arch.mcp.envelope import err, ok, resolve_repo, tool_result
from architecture_model.sil.decorators import instrumented

_REV_RE = re.compile(r"^\d{1,7}$")
_MODEL_REL = Path("model") / ".architecture-model.yaml"
_MANIFEST_REL = Path("manifest") / "manifest.json"
_DIGEST_REL = Path("digest.json")


@instrumented("mcp_tool:package_load")
@tool_result
async def package_load_tool(
    repo_path: str,
    revision: str | None = None,
) -> dict:
    """Load a published architecture package generation."""
    from architecture_model.lifecycle.package import load_package
    from architecture_model.lifecycle import generation_dir
    from architecture_model.lifecycle.publication import (
        list_generations,
        read_current_generation,
    )

    repo = resolve_repo(repo_path)
    tree = paths.ensure_all(repo)
    lifecycle_root = tree["package_root"]

    pkg_yaml = lifecycle_root / "package.yaml"
    if not pkg_yaml.exists():
        return err("NOT_FOUND", f"no package at {pkg_yaml}")

    pkg = load_package(lifecycle_root)

    # Resolve requested generation number.
    if revision is None:
        current = read_current_generation(pkg)
        if current is None:
            return err("NOT_FOUND", "no published generation")
        n = current
    else:
        if not isinstance(revision, str) or not _REV_RE.match(revision):
            return err(
                "INVALID_ARGUMENT",
                "revision must be a 7-digit generation number",
                revision=revision,
            )
        n = int(revision)
        if n not in list_generations(pkg):
            return err(
                "NOT_FOUND",
                "generation not found",
                revision=revision,
            )

    gen_dir = generation_dir(pkg, n)
    if not gen_dir.is_dir():
        return err(
            "NOT_FOUND",
            f"generation directory missing: {gen_dir}",
            revision=f"{n:07d}",
        )

    model_path = gen_dir / _MODEL_REL
    if not model_path.is_file():
        return err(
            "NOT_FOUND",
            f"model file missing in generation: {model_path}",
        )
    model_bytes = model_path.read_bytes()

    manifest_json: str | None = None
    manifest_path = gen_dir / _MANIFEST_REL
    if manifest_path.is_file():
        manifest_bytes = manifest_path.read_bytes()
        # Empty (0-byte) file is the "no manifest" sentinel written by
        # publish when ``manifest_json=None``. Any non-empty payload —
        # including a legitimate ``b"{}"`` — round-trips as-is.
        if manifest_bytes != b"":
            manifest_json = manifest_bytes.decode("utf-8")

    root_digest: str | None = None
    digest_path = gen_dir / _DIGEST_REL
    if digest_path.is_file():
        try:
            digest_doc = json.loads(digest_path.read_text(encoding="utf-8"))
            root_digest = digest_doc.get("root_digest")
        except (json.JSONDecodeError, OSError):
            root_digest = None

    return ok({
        "package_id": pkg.architecture_id,
        "revision": f"{n:07d}",
        "model_yaml": model_bytes.decode("utf-8"),
        "manifest_json": manifest_json,
        "root_digest": root_digest,
        "generation_dir": str(gen_dir),
    })
