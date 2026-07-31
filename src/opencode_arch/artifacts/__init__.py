"""Artifact selection and registry for model-driven SE document generation."""

from opencode_arch.artifacts.selector import (
    ArtifactSpec,
    ARTIFACT_REGISTRY,
    SUBSYSTEM_ARTIFACTS,
    SubsystemInfo,
    get_artifact_spec,
    select_artifacts,
    select_capability_detail_artifacts,
    select_subsystem_artifacts,
    should_decompose,
)
from opencode_arch.artifacts.templates import ArtifactTemplate, TemplateSection, TEMPLATES, get_template, API_DETAIL_TEMPLATE
from opencode_arch.artifacts.context import assemble_artifact_context, format_capability_detail_context
from opencode_arch.artifacts.diagrams import (
    generate_all_diagrams,
    generate_component_diagram,
    generate_dependency_diagram,
    generate_focused_diagram,
    generate_nav_diagram,
    generate_sequence_diagram,
)

__all__ = [
    "API_DETAIL_TEMPLATE",
    "ArtifactSpec",
    "ArtifactTemplate",
    "ARTIFACT_REGISTRY",
    "SUBSYSTEM_ARTIFACTS",
    "SubsystemInfo",
    "TEMPLATES",
    "TemplateSection",
    "assemble_artifact_context",
    "format_capability_detail_context",
    "generate_all_diagrams",
    "generate_component_diagram",
    "generate_dependency_diagram",
    "generate_focused_diagram",
    "generate_nav_diagram",
    "generate_sequence_diagram",
    "get_artifact_spec",
    "get_template",
    "select_artifacts",
    "select_capability_detail_artifacts",
    "select_subsystem_artifacts",
    "should_decompose",
]
