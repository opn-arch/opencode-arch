"""Tests for the G4 integration tool ``arch_integrate``.

``arch_integrate`` is a PURE surface wrapper over the openAG kernel
``integrate`` (B3 up-law): it reconstructs ``ChildContract`` dicts, runs the
sibling assume-satisfaction / parent-discharge checks, and surface-maps each
returned ``gap:integration-mismatch`` into a dict carrying a stable ``type``
alias and a deterministic ``diagnosis`` string.
"""
from __future__ import annotations

import asyncio

from opencode_arch.mcp.tools.arch_integrate import arch_integrate


def _run(coro):
    return asyncio.run(coro)


def _producer():
    return {
        "child": "COMP-SENSOR",
        "contract": {"attribute": "contract", "content": "IF-SENSOR", "role": "contract"},
        "guarantee": {
            "attribute": "behavior",
            "content": "delivers ±X every P",
            "role": "guarantee",
        },
        "assume": None,
    }


def _consumer(assume_content):
    return {
        "child": "COMP-CONTROLLER",
        "contract": {"attribute": "contract", "content": "IF-SENSOR", "role": "contract"},
        "guarantee": {
            "attribute": "behavior",
            "content": "dose ∈ CON-SAFE-BAND",
            "role": "guarantee",
        },
        "assume": {"attribute": "behavior", "content": assume_content, "role": "assume"},
    }


def test_arch_integrate_mismatch_surfaces_type_and_diagnosis():
    # consumer assumes something the producer does NOT guarantee → one gap
    out = _run(
        arch_integrate(
            children=[_producer(), _consumer("a DIFFERENT upstream contract")],
            interface_id="IF-SENSOR",
        )
    )
    assert out["ok"] is True
    assert out["converged"] is False
    gap = out["gaps"][0]
    assert gap["type"] == "gap:integration-mismatch"
    assert gap["gap_type"] == "gap:integration-mismatch"
    assert isinstance(gap["diagnosis"], str) and gap["diagnosis"]
    assert gap["entity_id"] == "IF-SENSOR"
    assert gap["promise_id"] == "IF-SENSOR#p-behavior"


def test_arch_integrate_converges_returns_no_gaps():
    # consumer assumes EXACTLY the producer's guarantee → composes
    out = _run(
        arch_integrate(
            children=[_producer(), _consumer("delivers ±X every P")],
            interface_id="IF-SENSOR",
        )
    )
    assert out["ok"] is True
    assert out["gaps"] == []
    assert out["converged"] is True


def test_arch_integrate_rejects_non_list_children():
    out = _run(arch_integrate(children="nope", interface_id="IF"))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_arch_integrate_rejects_empty_interface_id():
    out = _run(arch_integrate(children=[_producer()], interface_id="  "))
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"


def test_arch_integrate_rejects_malformed_child():
    out = _run(
        arch_integrate(children=[{"bogus": "key"}], interface_id="IF-SENSOR")
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_ARGUMENT"
