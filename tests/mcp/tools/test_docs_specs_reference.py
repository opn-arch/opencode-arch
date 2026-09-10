"""Task 25 — reference-doc formats rebuild via family6.* projectors.

Locks the contract that ``architect_docs`` supports the three
reference-documentation formats introduced by Phase 4:

* ``cli_reference`` → ``family6.cli_reference``
* ``api_reference`` → ``family6.api_reference``
* ``plugin_guide``  → ``family6.plugin_guide``

Each pair must be a valid (ViewSpec, ArtifactSpec) that points at a
registered projector in the ams DEFAULT_REGISTRY and renders via the
``markdown`` renderer.
"""
from __future__ import annotations

import pytest

from opencode_arch.mcp.tools.docs_specs import DEFAULT_SPECS, SUPPORTED_FORMATS


REFERENCE_FORMATS = ("cli_reference", "api_reference", "plugin_guide")


@pytest.mark.parametrize("fmt", REFERENCE_FORMATS)
def test_reference_format_is_supported(fmt):
    assert fmt in SUPPORTED_FORMATS
    assert fmt in DEFAULT_SPECS


@pytest.mark.parametrize("fmt", REFERENCE_FORMATS)
def test_reference_format_uses_family6_projector(fmt):
    view_spec, _artifact_spec = DEFAULT_SPECS[fmt]
    assert view_spec["projector"] == f"family6.{fmt}"


@pytest.mark.parametrize("fmt", REFERENCE_FORMATS)
def test_reference_format_projector_is_registered(fmt):
    from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY

    view_spec, _artifact_spec = DEFAULT_SPECS[fmt]
    assert view_spec["projector"] in DEFAULT_REGISTRY.list_names()


@pytest.mark.parametrize("fmt", REFERENCE_FORMATS)
def test_reference_format_renders_markdown(fmt):
    _view_spec, artifact_spec = DEFAULT_SPECS[fmt]
    assert artifact_spec["renderer"] == "markdown"
    assert artifact_spec["output_path"].endswith(".md")


@pytest.mark.parametrize("fmt", REFERENCE_FORMATS)
def test_reference_format_output_kind_is_markdown(fmt):
    view_spec, _artifact_spec = DEFAULT_SPECS[fmt]
    assert view_spec["output_content_kind"] == "markdown"


def test_reference_formats_included_in_default_all_expansion():
    """Reference docs are default-on: ``formats='all'`` must cover them.

    ``SUPPORTED_FORMATS`` is the canonical set that ``architect_docs``
    iterates when the caller passes ``formats='all'``. All three
    reference-doc formats MUST appear so downstream tooling generates
    them without an opt-in flag.
    """
    for fmt in REFERENCE_FORMATS:
        assert fmt in SUPPORTED_FORMATS, (
            f"reference-doc format {fmt!r} missing from SUPPORTED_FORMATS "
            "(reference docs are default-on per Phase 4)"
        )
