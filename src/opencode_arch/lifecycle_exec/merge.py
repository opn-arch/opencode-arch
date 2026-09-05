"""Three-way merge for :class:`ArchitectureModel` (T20).

Given a common ancestor (``base``) and two divergent descendants
(``local`` and ``remote``), :func:`three_way_merge` produces a merged
:class:`ArchitectureModel` plus a structured list of
:class:`Conflict` entries for anything the merger could not decide.

Semantics
---------
Entities (identified by ``id`` within their category):

* Present in all three: field-by-field 3-way merge.
* Present in base + local only (remote removed):
    - ``local == base`` -> accept removal.
    - Else -> conflict on ``__removed__``; keep local.
* Present in base + remote only: symmetric.
* Present only in local & remote (base absent):
    - Identical -> include (both agree).
    - Divergent -> conflict on ``__added_divergent__``; keep local.
* Present only in local (added) -> include; increments
  ``entities_added_local``.
* Present only in remote -> include; increments
  ``entities_added_remote``.
* Present only in base (both removed) -> drop, no conflict.

Relationships (keyed by ``(from, to, type)``): same shape as entities
but flagged with ``entity_id=None`` and ``field`` prefixed with
``"relationship:<from>:<to>:<type>"``.

Meta / other top-level keys: field-level 3-way merge.

Conflict placeholder policy
---------------------------
The merged model is always constructed even in the presence of
conflicts. For each conflicting scalar we keep the base value
(so unrelated fields still merge cleanly); for structural conflicts
(entity removed vs modified, entity divergently added) we keep the
local version. If the resulting dict fails to parse into an
:class:`ArchitectureModel` we raise :class:`MergeIntegrityError` —
this indicates the placeholder heuristic broke the schema.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from architecture_model.core.parser import _parse_raw
from architecture_model.core.types import ArchitectureModel

__all__ = [
    "Conflict",
    "MergeIntegrityError",
    "MergeResult",
    "three_way_merge",
]

_TOP_LEVEL_RESERVED = frozenset({"meta", "entities", "relationships"})

# Sentinel distinguishing "key missing" from "key present with value None".
_MISSING: Any = object()


class MergeIntegrityError(RuntimeError):
    """Raised when the merged dict fails to parse into a valid model."""


@dataclass(frozen=True)
class Conflict:
    entity_id: str | None
    field: str
    base: Any
    local: Any
    remote: Any


@dataclass(frozen=True)
class MergeResult:
    merged_model: ArchitectureModel
    conflicts: list[Conflict] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Field-level 3-way merge
# ---------------------------------------------------------------------------


def _merge_field_dict(
    base: dict,
    local: dict,
    remote: dict,
    *,
    entity_id: str | None,
    prefix: str = "",
) -> tuple[dict, list[Conflict]]:
    """3-way merge two flat dicts. Recursion not needed for our shapes."""
    merged: dict = {}
    conflicts: list[Conflict] = []
    keys = sorted(set(base) | set(local) | set(remote))
    for k in keys:
        bv = base.get(k, _MISSING)
        lv = local.get(k, _MISSING)
        rv = remote.get(k, _MISSING)
        # Case 1: both sides agree (possibly identical change or both missing).
        if lv == rv:
            if lv is not _MISSING:
                merged[k] = lv
            continue
        # Case 2: local unchanged from base → take remote.
        if lv == bv:
            if rv is not _MISSING:
                merged[k] = rv
            continue
        # Case 3: remote unchanged from base → take local.
        if rv == bv:
            if lv is not _MISSING:
                merged[k] = lv
            continue
        # Case 4: divergent change → conflict; keep base as placeholder.
        conflicts.append(
            Conflict(
                entity_id=entity_id,
                field=prefix + k,
                base=None if bv is _MISSING else bv,
                local=None if lv is _MISSING else lv,
                remote=None if rv is _MISSING else rv,
            )
        )
        if bv is not _MISSING:
            merged[k] = bv
        elif lv is not _MISSING:
            merged[k] = lv
    return merged, conflicts


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------


def _index_by_id(items: list[Any]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    if not isinstance(items, list):
        return result
    for entry in items:
        if isinstance(entry, dict) and "id" in entry:
            result[str(entry["id"])] = entry
    return result


def _merge_entity_category(
    b_list: list[Any],
    l_list: list[Any],
    r_list: list[Any],
    stats: dict[str, int],
) -> tuple[list[dict], list[Conflict]]:
    b_map, l_map, r_map = _index_by_id(b_list), _index_by_id(l_list), _index_by_id(r_list)
    all_ids = sorted(set(b_map) | set(l_map) | set(r_map))
    merged: list[dict] = []
    conflicts: list[Conflict] = []
    for eid in all_ids:
        in_b, in_l, in_r = eid in b_map, eid in l_map, eid in r_map
        b, l, r = b_map.get(eid), l_map.get(eid), r_map.get(eid)
        if in_b and in_l and in_r:
            m, cs = _merge_field_dict(b, l, r, entity_id=eid)
            merged.append(m)
            conflicts.extend(cs)
            if cs:
                stats["entities_conflicted"] += 1
            else:
                stats["entities_auto_merged"] += 1
        elif in_b and in_l and not in_r:
            if l == b:
                pass  # accept removal
            else:
                conflicts.append(
                    Conflict(entity_id=eid, field="__removed__", base=b, local=l, remote=None)
                )
                merged.append(l)
                stats["entities_conflicted"] += 1
        elif in_b and not in_l and in_r:
            if r == b:
                pass  # accept removal
            else:
                conflicts.append(
                    Conflict(entity_id=eid, field="__removed__", base=b, local=None, remote=r)
                )
                merged.append(r)
                stats["entities_conflicted"] += 1
        elif not in_b and in_l and in_r:
            if l == r:
                merged.append(l)
                stats["entities_auto_merged"] += 1
            else:
                conflicts.append(
                    Conflict(
                        entity_id=eid,
                        field="__added_divergent__",
                        base=None,
                        local=l,
                        remote=r,
                    )
                )
                merged.append(l)
                stats["entities_conflicted"] += 1
        elif not in_b and in_l and not in_r:
            merged.append(l)
            stats["entities_added_local"] += 1
        elif not in_b and not in_l and in_r:
            merged.append(r)
            stats["entities_added_remote"] += 1
        # in_b and not in_l and not in_r: both removed → drop, no conflict.
    return merged, conflicts


def _merge_entities(
    b_ent: dict,
    l_ent: dict,
    r_ent: dict,
    stats: dict[str, int],
) -> tuple[dict, list[Conflict]]:
    b_ent = b_ent or {}
    l_ent = l_ent or {}
    r_ent = r_ent or {}
    all_cats = sorted(set(b_ent) | set(l_ent) | set(r_ent))
    merged: dict = {}
    conflicts: list[Conflict] = []
    for cat in all_cats:
        m, cs = _merge_entity_category(
            b_ent.get(cat, []) or [],
            l_ent.get(cat, []) or [],
            r_ent.get(cat, []) or [],
            stats,
        )
        if m:
            merged[cat] = m
        conflicts.extend(cs)
    return merged, conflicts


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------


def _rel_key(r: dict) -> tuple[str, str, str]:
    return (str(r.get("from", "")), str(r.get("to", "")), str(r.get("type", "")))


def _index_rels(rels: list[Any]) -> dict[tuple[str, str, str], dict]:
    result: dict[tuple[str, str, str], dict] = {}
    if not isinstance(rels, list):
        return result
    for r in rels:
        if isinstance(r, dict):
            result[_rel_key(r)] = r
    return result


def _merge_relationships(
    b_rels: list[Any],
    l_rels: list[Any],
    r_rels: list[Any],
    stats: dict[str, int],
) -> tuple[list[dict], list[Conflict]]:
    b_map, l_map, r_map = _index_rels(b_rels), _index_rels(l_rels), _index_rels(r_rels)
    all_keys = sorted(set(b_map) | set(l_map) | set(r_map))
    merged: list[dict] = []
    conflicts: list[Conflict] = []
    for key in all_keys:
        in_b, in_l, in_r = key in b_map, key in l_map, key in r_map
        b, l, r = b_map.get(key), l_map.get(key), r_map.get(key)
        f, t, ty = key
        rel_label = f"relationship:{f}:{t}:{ty}"
        if in_b and in_l and in_r:
            m, cs = _merge_field_dict(b, l, r, entity_id=None, prefix=rel_label + ".")
            merged.append(m)
            conflicts.extend(cs)
            if cs:
                stats["relationships_conflicted"] += 1
            else:
                stats["relationships_auto_merged"] += 1
        elif in_b and in_l and not in_r:
            if l == b:
                pass
            else:
                conflicts.append(
                    Conflict(
                        entity_id=None,
                        field=rel_label + ":__removed__",
                        base=b,
                        local=l,
                        remote=None,
                    )
                )
                merged.append(l)
                stats["relationships_conflicted"] += 1
        elif in_b and not in_l and in_r:
            if r == b:
                pass
            else:
                conflicts.append(
                    Conflict(
                        entity_id=None,
                        field=rel_label + ":__removed__",
                        base=b,
                        local=None,
                        remote=r,
                    )
                )
                merged.append(r)
                stats["relationships_conflicted"] += 1
        elif not in_b and in_l and in_r:
            if l == r:
                merged.append(l)
                stats["relationships_auto_merged"] += 1
            else:
                conflicts.append(
                    Conflict(
                        entity_id=None,
                        field=rel_label + ":__added_divergent__",
                        base=None,
                        local=l,
                        remote=r,
                    )
                )
                merged.append(l)
                stats["relationships_conflicted"] += 1
        elif not in_b and in_l and not in_r:
            merged.append(l)
        elif not in_b and not in_l and in_r:
            merged.append(r)
        # in_b only: both removed → drop.
    return merged, conflicts


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def three_way_merge(
    base: ArchitectureModel,
    local: ArchitectureModel,
    remote: ArchitectureModel,
) -> MergeResult:
    """Merge ``local`` and ``remote`` against common ancestor ``base``."""
    b_raw = base.to_dict()
    l_raw = local.to_dict()
    r_raw = remote.to_dict()

    stats: dict[str, int] = {
        "entities_auto_merged": 0,
        "entities_conflicted": 0,
        "entities_added_local": 0,
        "entities_added_remote": 0,
        "relationships_auto_merged": 0,
        "relationships_conflicted": 0,
    }
    conflicts: list[Conflict] = []

    # meta
    merged_meta, meta_conflicts = _merge_field_dict(
        b_raw.get("meta", {}) or {},
        l_raw.get("meta", {}) or {},
        r_raw.get("meta", {}) or {},
        entity_id=None,
        prefix="meta.",
    )
    conflicts.extend(meta_conflicts)

    # entities
    merged_entities, ent_conflicts = _merge_entities(
        b_raw.get("entities", {}) or {},
        l_raw.get("entities", {}) or {},
        r_raw.get("entities", {}) or {},
        stats,
    )
    conflicts.extend(ent_conflicts)

    # relationships
    merged_rels, rel_conflicts = _merge_relationships(
        b_raw.get("relationships", []) or [],
        l_raw.get("relationships", []) or [],
        r_raw.get("relationships", []) or [],
        stats,
    )
    conflicts.extend(rel_conflicts)

    # Assemble.
    merged_dict: dict = {
        "meta": merged_meta,
        "entities": merged_entities,
        "relationships": merged_rels,
    }

    # Other top-level opaque keys: field-level 3-way merge.
    extra_keys = (
        (set(b_raw) | set(l_raw) | set(r_raw)) - _TOP_LEVEL_RESERVED
    )
    if extra_keys:
        top_b = {k: b_raw.get(k) for k in extra_keys if k in b_raw}
        top_l = {k: l_raw.get(k) for k in extra_keys if k in l_raw}
        top_r = {k: r_raw.get(k) for k in extra_keys if k in r_raw}
        top_merged, top_conflicts = _merge_field_dict(
            top_b, top_l, top_r, entity_id=None, prefix=""
        )
        for k, v in top_merged.items():
            merged_dict[k] = v
        conflicts.extend(top_conflicts)

    try:
        merged_model = _parse_raw(merged_dict)
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as exc:  # noqa: BLE001
        raise MergeIntegrityError(
            f"merged dict failed to parse: {type(exc).__name__}: {exc}"
        ) from exc

    return MergeResult(
        merged_model=merged_model,
        conflicts=conflicts,
        stats=stats,
    )
