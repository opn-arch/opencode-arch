"""Every supported doc format maps to a (ViewSpec, ArtifactSpec) pair
whose projector is registered in the ams DEFAULT_REGISTRY.

Task 12 (minimum-invasive) of Phase 1: this locks the format→projector
mapping table so a future Phase 2 task can rewrite generate_docs as
sugar over rebuild_artifacts without a schema archaeology exercise.
"""
import pytest

from opencode_arch.mcp.tools.docs_specs import DEFAULT_SPECS, SUPPORTED_FORMATS


def test_every_format_has_a_spec():
    missing = [f for f in SUPPORTED_FORMATS if f not in DEFAULT_SPECS]
    assert not missing, f"formats without DEFAULT_SPECS entry: {missing}"


@pytest.mark.parametrize("fmt", SUPPORTED_FORMATS)
def test_spec_maps_to_registered_projector(fmt):
    from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY

    view_spec, artifact_spec = DEFAULT_SPECS[fmt]
    assert view_spec["projector"] in DEFAULT_REGISTRY.list_names(), (
        f"format {fmt} references unregistered projector "
        f"{view_spec['projector']!r}"
    )
