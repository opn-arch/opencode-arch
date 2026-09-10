"""Phase 3 Task 20 — architect_docs formats='entity_pages' generates per-entity variants.

Opt-in (not part of ``all``). Walks the model and, for each supported
(family, entity_id) pair, writes a Markdown entity page under
``.architecture/lifecycle/artifacts/entity_pages/family{N}/{entity_id}.md``.
The family → supported-kinds map mirrors
``architecture_model.lifecycle.projectors.drill._FAMILY_KINDS``.
"""

from __future__ import annotations

import asyncio
import textwrap
from pathlib import Path

from opencode_arch.mcp.tools.docs import generate_docs


def _run(coro):
    return asyncio.run(coro)


def _write_model(tmp_path: Path) -> None:
    (tmp_path / ".architecture-model.yaml").write_text(
        textwrap.dedent(
            """\
            meta:
              project: entity-pages-fixture
              schema_version: '2.1'
            entities:
              components:
                - id: COMP-1
                  name: Alpha
                  status: ACTIVE
                  intent: Alpha does A.
                - id: COMP-2
                  name: Beta
                  status: ACTIVE
                  intent: Beta does B.
              capabilities:
                - id: CAP-F1
                  name: SomeCap
                  status: ACTIVE
                  intent: Provides some capability.
              interfaces:
                - id: IF-1
                  name: SomeIface
                  type: internal
                  status: ACTIVE
                  intent: Public API.
              environments:
                - id: ENV-1
                  name: Prod
                  status: ACTIVE
                  kind: production
                  region: us-east-1
              resources:
                - id: RES-1
                  name: DB
                  status: ACTIVE
                  kind: database
                  provider: aws
            relationships:
              - from: COMP-1
                to: CAP-F1
                type: realizes
              - from: COMP-1
                to: IF-1
                type: exposes
              - from: COMP-1
                to: ENV-1
                type: allocated-to
              - from: COMP-1
                to: RES-1
                type: consumes
            """
        )
    )


def test_entity_pages_writes_expected_layout(tmp_path):
    _write_model(tmp_path)
    result = _run(generate_docs(str(tmp_path), formats="entity_pages"))
    assert result.get("error") is None or "error" not in result

    root = tmp_path / ".architecture" / "lifecycle" / "artifacts" / "entity_pages"
    assert root.is_dir(), f"entity_pages root not created: {root}"

    # family1 is the broadest: every entity kind gets a page.
    fam1 = root / "family1"
    assert fam1.is_dir()
    assert (fam1 / "COMP-1.md").is_file()
    assert (fam1 / "COMP-2.md").is_file()
    assert (fam1 / "CAP-F1.md").is_file()
    assert (fam1 / "IF-1.md").is_file()

    # A body sample must contain the entity's own id somewhere.
    body = (fam1 / "COMP-1.md").read_text()
    assert "Alpha" in body or "COMP-1" in body

    # Report must enumerate the files it wrote.
    generated = result.get("generated", [])
    joined = "\n".join(generated)
    assert "entity_pages/family1/COMP-1.md" in joined


def test_entity_pages_not_part_of_all(tmp_path):
    _write_model(tmp_path)
    result = _run(generate_docs(str(tmp_path), formats="all"))
    root = tmp_path / ".architecture" / "lifecycle" / "artifacts" / "entity_pages"
    # ``all`` must not emit entity_pages — opt-in only.
    assert not root.exists(), "entity_pages must not be produced by formats='all'"
    # ``all`` must still succeed at whatever it does.
    assert result.get("error") is None or "error" not in result


def test_entity_pages_covers_multiple_families(tmp_path):
    _write_model(tmp_path)
    _run(generate_docs(str(tmp_path), formats="entity_pages"))
    root = tmp_path / ".architecture" / "lifecycle" / "artifacts" / "entity_pages"
    # At least family1 (broad) and family3 (component / layer) should exist.
    assert (root / "family1").is_dir()
    assert (root / "family3").is_dir()
    assert (root / "family3" / "COMP-1.md").is_file()


def test_entity_pages_family5_deployment(tmp_path):
    """Family 5 renders deployment pages for environments and resources."""
    _write_model(tmp_path)
    _run(generate_docs(str(tmp_path), formats="entity_pages"))
    root = tmp_path / ".architecture" / "lifecycle" / "artifacts" / "entity_pages"
    fam5 = root / "family5"
    assert fam5.is_dir(), "family5 entity_pages directory missing"
    assert (fam5 / "ENV-1.md").is_file()
    assert (fam5 / "RES-1.md").is_file()
    env_body = (fam5 / "ENV-1.md").read_text()
    assert "## Kind" in env_body and "production" in env_body
    assert "## Region" in env_body and "us-east-1" in env_body
    assert "## Deployed Components" in env_body and "COMP-1" in env_body
    res_body = (fam5 / "RES-1.md").read_text()
    assert "## Kind" in res_body and "database" in res_body
    assert "## Provider" in res_body and "aws" in res_body
    assert "## Consumed By" in res_body and "COMP-1" in res_body
    # Component page in family5 shows Deployed To.
    comp_body = (fam5 / "COMP-1.md").read_text()
    assert "## Deployed To" in comp_body and "ENV-1" in comp_body
