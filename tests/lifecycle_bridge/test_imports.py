"""Tests for the lifecycle_bridge re-export layer."""
from __future__ import annotations

import importlib
from unittest import mock

import pytest


def test_all_symbols_importable():
    bridge = importlib.import_module("opencode_arch.lifecycle_bridge")
    for name in bridge.__all__:
        assert getattr(bridge, name, None) is not None, f"{name} missing/None"


def test_schema_versions_work_order_is_1_0_0():
    from opencode_arch.lifecycle_bridge import SchemaVersions
    assert SchemaVersions.WORK_ORDER == "1.0.0"


def test_proposal_types_registry_has_six_entries():
    from opencode_arch.lifecycle_bridge import PROPOSAL_TYPES
    assert len(PROPOSAL_TYPES) == 6


def test_proposal_from_dict_dispatches():
    from opencode_arch.lifecycle_bridge import proposal_from_dict
    data = {
        "kind": "model-patch",
        "provenance": {
            "work_order_id": "wo-1",
            "model_version": "2.1.0",
            "prompt_digest": "sha256:abc",
        },
        "operations": [{"op": "add", "path": "/x", "value": 1}],
    }
    prop = proposal_from_dict(data)
    assert prop.kind.value == "model-patch"


def test_job_state_enum_has_eight_values():
    from opencode_arch.lifecycle_bridge import JobState
    assert len(list(JobState)) == 8


def test_invalid_transition_error_is_exception():
    from opencode_arch.lifecycle_bridge import InvalidTransitionError
    assert issubclass(InvalidTransitionError, Exception)


def test_validate_proposal_alias_matches():
    import architecture_model.ai.validators as v
    from opencode_arch.lifecycle_bridge import validate_proposal
    assert validate_proposal is v.validate


def test_bridge_all_matches_actual_exports():
    bridge = importlib.import_module("opencode_arch.lifecycle_bridge")
    assert set(dir(bridge)) >= set(bridge.__all__)


def test_version_guard_message():
    import sys
    sys.modules.pop("opencode_arch.lifecycle_bridge", None)
    with mock.patch(
        "architecture_model.lifecycle.versions.SchemaVersions.WORK_ORDER",
        "9.9.9",
    ):
        with pytest.raises(ImportError) as exc:
            importlib.import_module("opencode_arch.lifecycle_bridge")
        msg = str(exc.value)
        assert "Phase 1" in msg
        assert "9.9.9" in msg
    sys.modules.pop("opencode_arch.lifecycle_bridge", None)
    importlib.import_module("opencode_arch.lifecycle_bridge")
