"""Model-dir persistence parity: the writer tools must populate
``.architecture/model/*.v3.yaml`` so the round/read tools can load it.

Before this behavior existed, ``arch_pipeline`` / ``arch_extract`` only wrote
generations under ``.architecture/generations/openAG-tool`` and the round-centric
read tools (``arch_health`` etc.) raised ``FileNotFoundError`` because nothing
populated the model dir.
"""

from __future__ import annotations

import asyncio

from opencode_arch.mcp.tools.arch_pipeline import arch_pipeline
from opencode_arch.mcp.tools.arch_extract import arch_extract
from opencode_arch.mcp.tools.arch_health import arch_health
from opencode_arch.mcp.tools._openag_loader import load_doc


def _seed_repo(root):
    (root / ".architecture").mkdir(parents=True)
    src = root / "src"
    src.mkdir()
    (src / "a.py").write_text("from src import b\nimport os\n", encoding="utf-8")
    (src / "b.py").write_text("x = 1\n", encoding="utf-8")
    return root


def _model_dir(repo):
    return repo / ".architecture" / "model"


def test_pipeline_writes_loadable_model_dir(tmp_path):
    repo = _seed_repo(tmp_path / "pl")
    out = asyncio.run(arch_pipeline(repo_path=str(repo)))
    assert out["ok"] is True

    assert (_model_dir(repo) / "model.v3.yaml").is_file()
    assert out.get("model_dir")

    # Round/read loader now succeeds (previously FileNotFoundError).
    doc = load_doc(str(repo))
    assert "entities" in doc


def test_pipeline_unblocks_arch_health(tmp_path):
    repo = _seed_repo(tmp_path / "health")
    asyncio.run(arch_pipeline(repo_path=str(repo)))

    out = asyncio.run(arch_health(repo_path=str(repo)))
    assert out["ok"] is True


def test_extract_writes_loadable_model_dir(tmp_path):
    repo = _seed_repo(tmp_path / "ex")
    out = asyncio.run(arch_extract(repo_path=str(repo)))
    assert out["ok"] is True

    assert (_model_dir(repo) / "model.v3.yaml").is_file()
    doc = load_doc(str(repo))
    assert "entities" in doc
