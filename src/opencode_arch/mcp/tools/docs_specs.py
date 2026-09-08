"""Default ViewSpec + ArtifactSpec pairs for every architect_docs format.

Task 12 (Phase 1, minimum-invasive scope): this module ONLY declares
the mapping table. The legacy `generate_docs` tool in ``docs.py``
still owns rendering. A future Phase 2 task will rewrite the tool as
sugar over ``rebuild_artifacts`` once ArtifactSpec supports multi-file
outputs (behaviors/, diagrams/) and manifest hydration is proceduralized.

Downstream expectation: every projector name in ``_PROJECTOR_MAP`` must
be registered in ``architecture_model.lifecycle.view_projection.DEFAULT_REGISTRY``
(seeded by Tasks 6 + 7).
"""
from __future__ import annotations

SUPPORTED_FORMATS: tuple[str, ...] = (
    "conops",
    "functional_analysis",
    "logical_architecture",
    "operations_manual",
    "maintenance_manual",
    "use_cases",
    "deployment_guide",
    "interface_spec",
    "api_reference",
    "cli_reference",
    "plugin_guide",
    "data_model",
    "requirements_analysis",
    "verification_validation",
    "risk_assessment",
    "security_analysis",
    "artifact_traceability",
    "component_spec",
    "icd",
    "dependency_matrix",
    "health",
    "drift",
    "system_design",
    "integration_flows",
    "behavior_spec",
    "index",
)

_PROJECTOR_MAP: dict[str, str] = {
    "conops":                     "family1.conops",
    "functional_analysis":        "family2.functional_analysis",
    "logical_architecture":       "family3.logical_architecture",
    "operations_manual":          "family4.operations_manual",
    "maintenance_manual":         "family4.maintenance_manual",
    "use_cases":                  "family4.use_cases",
    "deployment_guide":           "family5.deployment_guide",
    "interface_spec":             "family6.interface_spec",
    "api_reference":              "family6.api_reference",
    "cli_reference":              "family6.cli_reference",
    "plugin_guide":               "family6.plugin_guide",
    "data_model":                 "family6.data_model",
    "requirements_analysis":      "family7.requirements_analysis",
    "verification_validation":    "family7.verification_validation",
    "risk_assessment":            "family7.risk_assessment",
    "security_analysis":          "family7.security_analysis",
    "artifact_traceability":      "family7.artifact_traceability",
    "component_spec":             "family3.component_spec",
    "icd":                        "family6.icd",
    "dependency_matrix":          "family3.dependency_matrix",
    "health":                     "family8.health",
    "drift":                      "family8.drift",
    "system_design":              "family3.system_design",
    "integration_flows":          "family4.integration_flows",
    "behavior_spec":              "family4.behavior_spec",
    "index":                      "family8.index",
}


def _default_view_spec(fmt: str) -> dict:
    return {
        "id": f"docs.{fmt}",
        "slice_ref": {"slice_id": f"docs.{fmt}.slice", "model_revision": "CURRENT"},
        "projector": _PROJECTOR_MAP[fmt],
        "output_content_kind": "markdown",
    }


def _default_artifact_spec(fmt: str) -> dict:
    return {
        "id": f"docs.{fmt}",
        "renderer": "markdown",
        "view_refs": [f"docs.{fmt}"],
        "output_path": f"docs/architecture/{fmt}.md",
    }


DEFAULT_SPECS: dict[str, tuple[dict, dict]] = {
    fmt: (_default_view_spec(fmt), _default_artifact_spec(fmt))
    for fmt in SUPPORTED_FORMATS
}
