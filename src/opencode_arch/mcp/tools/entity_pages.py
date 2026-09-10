"""Phase 3 Task 20 — generate per-entity Markdown pages via ``EntityPageProjector``.

Opt-in helper called from ``architect_docs`` when ``formats='entity_pages'``.
For each family in :data:`_FAMILY_KINDS` and each entity of a supported
kind, produce a Markdown file at
``.architecture/lifecycle/artifacts/entity_pages/family{N}/{entity_id}.md``.

Direct-projection path: this module skips the full lifecycle rebuild
(ArchitecturePackage → ModelSlice → materialize → project → renderer)
because the entity-page projectors do not depend on cross-package data
or supplementary fragments beyond what can be reconstructed in-process.
Behaviour matches ``project()`` for the ``__scope_*`` config keys.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Family → tuple of entity-collection attribute names (mirrors
# ``architecture_model.lifecycle.projectors.drill._FAMILY_KINDS``).
_FAMILY_KINDS: dict[int, tuple[str, ...]] = {
    1: ("actors", "capabilities", "behaviors", "interfaces", "constraints", "layers", "components"),
    2: ("capabilities", "components", "behaviors"),
    3: ("components", "layers"),
    4: ("behaviors", "actors"),
    5: ("components", "environments", "resources"),
    6: ("interfaces", "components"),
    7: ("components", "capabilities", "behaviors", "interfaces", "constraints"),
    8: ("components", "capabilities", "interfaces"),
}


def _kind_singular(field: str) -> str:
    """Convert an entities-collection field name to the singular kind."""
    if field.endswith("ies"):
        return field[:-3] + "y"
    if field.endswith("s") and not field.endswith("ss"):
        return field[:-1]
    return field


def generate_entity_pages(model: Any, out_root: Path) -> list[Path]:
    """Write per-entity Markdown pages under ``out_root``.

    Args:
        model: Parsed :class:`ArchitectureModel`.
        out_root: Directory to write ``family{N}/{entity_id}.md`` files under.
            Typically ``<repo>/.architecture/lifecycle/artifacts/entity_pages``.

    Returns:
        Sorted list of written file paths.
    """
    from architecture_model.core.slicer import slice_by_entity
    from architecture_model.lifecycle.model_slice_materializer import (
        _compute_entity_scope_metadata,
    )
    from architecture_model.lifecycle.projectors.entity_pages import (
        Family1EntityPage,
        Family2EntityPage,
        Family3EntityPage,
        Family4EntityPage,
        Family5EntityPage,
        Family6EntityPage,
        Family7EntityPage,
        Family8EntityPage,
    )

    # Direct-instantiation table — entity_page projectors are not seeded
    # into the ``DEFAULT_REGISTRY`` (see docstring on
    # ``EntityPageProjector``: they dispatch on ``__scope_entity_kind``
    # rather than a per-kind registry entry).
    _PROJECTORS: dict[int, Any] = {
        1: Family1EntityPage(),
        2: Family2EntityPage(),
        3: Family3EntityPage(),
        4: Family4EntityPage(),
        5: Family5EntityPage(),
        6: Family6EntityPage(),
        7: Family7EntityPage(),
        8: Family8EntityPage(),
    }

    out_root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    # Cache per-entity scope metadata + sub-model to avoid recomputing across families.
    scope_cache: dict[str, tuple[dict, Any]] = {}

    def _scope_for(entity_id: str) -> tuple[dict, Any]:
        if entity_id in scope_cache:
            return scope_cache[entity_id]
        meta = _compute_entity_scope_metadata(model, entity_id)
        try:
            sub_model = slice_by_entity(model, entity_id)
        except KeyError:
            sub_model = model
        scope_cache[entity_id] = (meta, sub_model)
        return scope_cache[entity_id]

    for family, fields in sorted(_FAMILY_KINDS.items()):
        projector_fn = _PROJECTORS.get(family)
        if projector_fn is None:
            continue

        family_dir = out_root / f"family{family}"
        for field in fields:
            entities = getattr(model.entities, field, ()) or ()
            if not entities:
                continue
            for ent in entities:
                entity_id = getattr(ent, "id", None)
                if not entity_id:
                    continue
                meta, sub_model = _scope_for(entity_id)
                config = {
                    "__scope_entity_id": meta["scope_entity_id"],
                    "__scope_entity_kind": _kind_singular(field),
                    "__scope_inbound_depends_on": tuple(meta.get("inbound_depends_on", ())),
                    "__scope_outbound_by_type": dict(meta.get("outbound_by_type", {}) or {}),
                    "__scope_inbound_by_type": dict(meta.get("inbound_by_type", {}) or {}),
                    "__scope_contains_descendants": tuple(
                        meta.get("contains_descendants", ()) or ()
                    ),
                }
                try:
                    spec = projector_fn(sub_model, config)
                except NotImplementedError:
                    # Family does not render this specific kind (rare — shape
                    # of ``_FAMILY_KINDS`` already filters, but projectors may
                    # decline).
                    continue
                except Exception:
                    continue
                body = ""
                facets = getattr(spec, "facets", None) or {}
                if isinstance(facets, dict):
                    body = str(facets.get("body", "") or "")
                if not body:
                    continue
                family_dir.mkdir(parents=True, exist_ok=True)
                out_path = family_dir / f"{entity_id}.md"
                out_path.write_text(body)
                written.append(out_path)

    written.sort()
    return written


__all__ = ["generate_entity_pages", "_FAMILY_KINDS"]
