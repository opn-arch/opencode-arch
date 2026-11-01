"""Proposer plugin fixtures for ``arch_job_run`` parity tests.

Importable as a top-level module (``_openag_proposer_fixtures``) via the
``sys.path.insert`` trick in ``test_parity_job_run.py``, so proposer config
``plugin`` refs of the form ``_openag_proposer_fixtures:valid_patch`` resolve.
Shapes are openAG-native ModelPatch dicts, NOT AMS Proposal objects.
"""
from __future__ import annotations


def valid_patch(_wo):
    """Return a valid openAG ModelPatch dict (add entity C2 + contains edge)."""
    return {
        "ops": [
            {
                "kind": "add",
                "target": "entity",
                "value": {"id": "C2", "name": "Two", "kind": "Component"},
                "entity_kind": "components",
            },
            {
                "kind": "add",
                "target": "relationship",
                "value": {"from": "C1", "to": "C2", "type": "contains"},
            },
        ]
    }


def invalid_patch(_wo):
    """Return a ModelPatch with an unsupported ``move`` op (fails validation)."""
    return {"ops": [{"kind": "move", "target": "entity", "value": {"id": "C1"}}]}


NOT_A_FUNCTION = 123
