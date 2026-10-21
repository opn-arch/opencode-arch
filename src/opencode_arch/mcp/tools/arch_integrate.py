"""G4 integration tool: ``arch_integrate``.

A PURE surface wrapper over the openAG kernel ``integrate`` (B3 up-law —
the only step where sibling guarantees are checked against one another).
It reconstructs ``ChildContract`` dataclasses from plain dicts (as emitted
by ``arch_allocate_contract`` via ``dataclasses.asdict``), runs the
sibling assume-satisfaction / parent-discharge checks, and surface-maps
each returned ``gap:integration-mismatch`` into a dict carrying a stable
``type`` alias and a deterministic ``diagnosis`` string.

Imports of ``openag`` are lazy so this module stays importable without
the dependency present.
"""
from __future__ import annotations

from opencode_arch.mcp.envelope import tool_result


def _diagnosis(interface_id: str, promise_id: str) -> str:
    """Deterministic natural-language explanation of a composition failure."""
    return (
        f"interface {interface_id} does not compose: a child's assumed "
        "upstream contract is not met by a sibling guarantee (or the children "
        "fail to discharge the parent guarantee); counterexample localized to "
        f"promise {promise_id}"
    )


@tool_result
async def arch_integrate(
    children: list[dict],
    interface_id: str,
    parent_guarantee: dict | None = None,
) -> dict:
    """Run the B3 integration round over an interface's children (pure).

    Returns ``{"gaps": [...], "converged": bool}`` where each gap keeps the
    kernel ``gap_type`` and adds a ``type`` alias plus a deterministic
    ``diagnosis``. ``converged`` is True iff no gaps were emitted.
    """
    if not isinstance(children, list):
        raise ValueError("children must be a list")
    if not isinstance(interface_id, str) or not interface_id.strip():
        raise ValueError("interface_id must be a non-empty string")
    for child in children:
        if not isinstance(child, dict):
            raise ValueError("each child must be a dict")

    from openag.kernel.contracts import ChildContract
    from openag.kernel.integrate import integrate

    contracts = []
    for child in children:
        try:
            contracts.append(ChildContract(**child))
        except TypeError as exc:
            raise ValueError(f"malformed child contract: {exc}")

    raw_gaps = integrate(contracts, interface_id, parent_guarantee=parent_guarantee)

    gaps = []
    for gap in raw_gaps:
        gap_type = gap["gap_type"]
        promise_id = gap["promise_id"]
        gaps.append(
            {
                "gap_type": gap_type,
                "type": gap_type,
                "promise_id": promise_id,
                "entity_id": gap["entity_id"],
                "diagnosis": _diagnosis(interface_id, promise_id),
            }
        )

    return {"gaps": gaps, "converged": len(gaps) == 0}
