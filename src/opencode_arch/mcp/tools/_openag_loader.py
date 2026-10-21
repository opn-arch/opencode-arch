"""Shared openAG model-loading helpers for the round-centric MCP tools.

The openAG model lives at ``<repo_path>/.architecture/model/`` as a
directory of ``*.v3.yaml`` fragments. These helpers resolve + validate the
repo, merge the fragments into a single doc, and build the in-memory
:class:`~openag.graph.model_graph.ModelGraph`. Imports of ``openag`` are
lazy so the tools module stays importable without the dependency present.
"""
from __future__ import annotations

from pathlib import Path

from opencode_arch.mcp.envelope import resolve_repo

_MODEL_REL = Path(".architecture") / "model"


def load_doc(repo_path: str):
    """Resolve the repo + openAG model dir and return the merged doc.

    Raises:
        ValueError / FileNotFoundError / NotADirectoryError: from
            ``resolve_repo`` (repo-level validation).
        FileNotFoundError: when the openAG model dir is absent or empty.
    """
    repo = resolve_repo(repo_path)
    model_dir = repo / _MODEL_REL
    if not model_dir.is_dir():
        raise FileNotFoundError(f"openAG model dir not found: {model_dir}")
    if not any(model_dir.glob("*.v3.yaml")):
        raise FileNotFoundError(f"openAG model dir is empty: {model_dir}")

    from openag.model_io import load_model_dir

    return load_model_dir(str(model_dir))


def build_graph(doc):
    """Build the in-memory :class:`ModelGraph` from a merged doc."""
    from openag.graph.model_graph import ModelGraph

    return ModelGraph.from_doc(doc)
