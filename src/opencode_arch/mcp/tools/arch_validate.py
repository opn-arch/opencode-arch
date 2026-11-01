"""arch_validate — native model validation + scoring MCP tool over openAG.

Behavioral replacement for the legacy AMS ``architect_validate`` tool. Parses
or loads a model doc, runs schema + axis-canonicality lint, and projects the
resulting gap-list into a bounded 0-100 score via
:func:`openag.validate.validate_scored`. No legacy ``architecture_model``
dependency.

Accepts either an inline ``model_yaml`` string or (when empty) loads the
repo's merged openAG model doc from ``<repo_path>/.architecture/model/``.
"""

from __future__ import annotations

import yaml

from opencode_arch.mcp._arch_tool import arch_tool


@arch_tool
async def arch_validate(repo_path: str = "", model_yaml: str = "") -> dict:
    """Validate a model (schema + axis lint) and return a bounded score."""
    if model_yaml and model_yaml.strip():
        doc = yaml.safe_load(model_yaml)
        if doc is None:
            raise ValueError("empty model_yaml document")
    else:
        from opencode_arch.mcp.tools._openag_loader import load_doc

        doc = load_doc(repo_path)

    from openag.validate import validate_scored

    return validate_scored(doc)
