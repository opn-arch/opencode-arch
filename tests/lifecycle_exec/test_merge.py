"""Tests for lifecycle_exec.merge — three-way merge (T20)."""
from __future__ import annotations

import pytest

from architecture_model.core.parser import _parse_raw

from opencode_arch.lifecycle_exec import merge as merge_mod
from opencode_arch.lifecycle_exec.merge import (
    Conflict,
    MergeIntegrityError,
    MergeResult,
    three_way_merge,
)


def _mk(components=None, relationships=None, meta=None):
    """Build an ArchitectureModel from a compact dict of components/rels."""
    m = {
        "schema_version": "2.0",
        "project": "t",
        "generated_at": "2026-01-01T00:00:00+00:00",
    }
    if meta:
        m.update(meta)
    raw = {
        "meta": m,
        "entities": {"components": components or []},
        "relationships": relationships or [],
    }
    return _parse_raw(raw)


def _comp(cid, name="X", **extra):
    return {"id": cid, "name": name, "status": "ACTIVE", **extra}


def _rel(f, t, ty="depends-on", **extra):
    return {"from": f, "to": t, "type": ty, **extra}


# --------------------------------------------------------------------- basics


def test_identity_merge_no_conflicts():
    base = _mk([_comp("COMP-1")])
    res = three_way_merge(base, base, base)
    assert isinstance(res, MergeResult)
    assert res.conflicts == []
    ids = [c.id for c in res.merged_model.entities.components]
    assert ids == ["COMP-1"]
    assert res.stats["entities_auto_merged"] == 1


def test_local_only_field_change_taken():
    base = _mk([_comp("COMP-1", name="A")])
    local = _mk([_comp("COMP-1", name="B")])
    remote = _mk([_comp("COMP-1", name="A")])
    res = three_way_merge(base, local, remote)
    assert res.conflicts == []
    assert res.merged_model.entities.components[0].name == "B"
    assert res.stats["entities_auto_merged"] == 1


def test_remote_only_field_change_taken():
    base = _mk([_comp("COMP-1", name="A")])
    local = _mk([_comp("COMP-1", name="A")])
    remote = _mk([_comp("COMP-1", name="C")])
    res = three_way_merge(base, local, remote)
    assert res.conflicts == []
    assert res.merged_model.entities.components[0].name == "C"


def test_same_change_on_both_sides_no_conflict():
    base = _mk([_comp("COMP-1", name="A")])
    local = _mk([_comp("COMP-1", name="Z")])
    remote = _mk([_comp("COMP-1", name="Z")])
    res = three_way_merge(base, local, remote)
    assert res.conflicts == []
    assert res.merged_model.entities.components[0].name == "Z"


def test_divergent_field_change_conflict_and_base_placeholder():
    base = _mk([_comp("COMP-1", name="A")])
    local = _mk([_comp("COMP-1", name="B")])
    remote = _mk([_comp("COMP-1", name="C")])
    res = three_way_merge(base, local, remote)
    assert len(res.conflicts) == 1
    c = res.conflicts[0]
    assert c.entity_id == "COMP-1"
    assert c.field == "name"
    assert c.base == "A" and c.local == "B" and c.remote == "C"
    # Placeholder in merged = base.
    assert res.merged_model.entities.components[0].name == "A"
    assert res.stats["entities_conflicted"] == 1


# -------------------------------------------------------------------- adds


def test_local_adds_entity():
    base = _mk([_comp("COMP-1")])
    local = _mk([_comp("COMP-1"), _comp("COMP-2")])
    remote = _mk([_comp("COMP-1")])
    res = three_way_merge(base, local, remote)
    assert res.conflicts == []
    ids = {c.id for c in res.merged_model.entities.components}
    assert ids == {"COMP-1", "COMP-2"}
    assert res.stats["entities_added_local"] == 1


def test_remote_adds_entity():
    base = _mk([_comp("COMP-1")])
    local = _mk([_comp("COMP-1")])
    remote = _mk([_comp("COMP-1"), _comp("COMP-3")])
    res = three_way_merge(base, local, remote)
    assert res.conflicts == []
    ids = {c.id for c in res.merged_model.entities.components}
    assert ids == {"COMP-1", "COMP-3"}
    assert res.stats["entities_added_remote"] == 1


def test_both_add_identical_entity_no_conflict():
    base = _mk([_comp("COMP-1")])
    local = _mk([_comp("COMP-1"), _comp("COMP-2", name="X")])
    remote = _mk([_comp("COMP-1"), _comp("COMP-2", name="X")])
    res = three_way_merge(base, local, remote)
    assert res.conflicts == []
    ids = {c.id for c in res.merged_model.entities.components}
    assert ids == {"COMP-1", "COMP-2"}
    assert res.stats["entities_auto_merged"] >= 1


def test_both_add_divergent_entity_conflict_keep_local():
    base = _mk([_comp("COMP-1")])
    local = _mk([_comp("COMP-1"), _comp("COMP-2", name="LocalName")])
    remote = _mk([_comp("COMP-1"), _comp("COMP-2", name="RemoteName")])
    res = three_way_merge(base, local, remote)
    assert len(res.conflicts) == 1
    c = res.conflicts[0]
    assert c.entity_id == "COMP-2"
    assert c.field == "__added_divergent__"
    # Placeholder = local
    got = [x for x in res.merged_model.entities.components if x.id == "COMP-2"][0]
    assert got.name == "LocalName"


# -------------------------------------------------------------------- removes


def test_local_removes_remote_unchanged_accept_removal():
    base = _mk([_comp("COMP-1"), _comp("COMP-2")])
    local = _mk([_comp("COMP-1")])
    remote = _mk([_comp("COMP-1"), _comp("COMP-2")])
    res = three_way_merge(base, local, remote)
    assert res.conflicts == []
    ids = {c.id for c in res.merged_model.entities.components}
    assert ids == {"COMP-1"}


def test_remote_removes_local_unchanged_accept_removal():
    base = _mk([_comp("COMP-1"), _comp("COMP-2")])
    local = _mk([_comp("COMP-1"), _comp("COMP-2")])
    remote = _mk([_comp("COMP-1")])
    res = three_way_merge(base, local, remote)
    assert res.conflicts == []
    ids = {c.id for c in res.merged_model.entities.components}
    assert ids == {"COMP-1"}


def test_local_removes_remote_modified_conflict():
    base = _mk([_comp("COMP-1"), _comp("COMP-2", name="A")])
    local = _mk([_comp("COMP-1")])
    remote = _mk([_comp("COMP-1"), _comp("COMP-2", name="B")])
    res = three_way_merge(base, local, remote)
    assert len(res.conflicts) == 1
    c = res.conflicts[0]
    assert c.entity_id == "COMP-2"
    assert c.field == "__removed__"
    assert c.local is None
    # Placeholder = remote (modified side kept).
    got = [x for x in res.merged_model.entities.components if x.id == "COMP-2"]
    assert got and got[0].name == "B"


def test_remote_removes_local_modified_conflict():
    base = _mk([_comp("COMP-1"), _comp("COMP-2", name="A")])
    local = _mk([_comp("COMP-1"), _comp("COMP-2", name="B")])
    remote = _mk([_comp("COMP-1")])
    res = three_way_merge(base, local, remote)
    assert len(res.conflicts) == 1
    c = res.conflicts[0]
    assert c.entity_id == "COMP-2"
    assert c.field == "__removed__"
    assert c.remote is None
    got = [x for x in res.merged_model.entities.components if x.id == "COMP-2"]
    assert got and got[0].name == "B"


def test_both_remove_entity_no_conflict():
    base = _mk([_comp("COMP-1"), _comp("COMP-2")])
    local = _mk([_comp("COMP-1")])
    remote = _mk([_comp("COMP-1")])
    res = three_way_merge(base, local, remote)
    assert res.conflicts == []
    ids = {c.id for c in res.merged_model.entities.components}
    assert ids == {"COMP-1"}


# ------------------------------------------------------------- relationships


def test_relationship_both_add_identical_no_conflict():
    base = _mk([_comp("COMP-1"), _comp("COMP-2")], [])
    rel = _rel("COMP-1", "COMP-2")
    local = _mk([_comp("COMP-1"), _comp("COMP-2")], [rel])
    remote = _mk([_comp("COMP-1"), _comp("COMP-2")], [rel])
    res = three_way_merge(base, local, remote)
    assert res.conflicts == []
    assert res.stats["relationships_auto_merged"] == 1
    assert len(res.merged_model.relationships) == 1


def test_relationship_one_side_removed_other_unchanged_accept_removal():
    rel = _rel("COMP-1", "COMP-2")
    base = _mk([_comp("COMP-1"), _comp("COMP-2")], [rel])
    local = _mk([_comp("COMP-1"), _comp("COMP-2")], [])
    remote = _mk([_comp("COMP-1"), _comp("COMP-2")], [rel])
    res = three_way_merge(base, local, remote)
    assert res.conflicts == []
    assert res.merged_model.relationships == []


def test_relationship_auxiliary_field_diverges_conflict():
    base = _mk(
        [_comp("COMP-1"), _comp("COMP-2")],
        [_rel("COMP-1", "COMP-2", description="orig")],
    )
    local = _mk(
        [_comp("COMP-1"), _comp("COMP-2")],
        [_rel("COMP-1", "COMP-2", description="local")],
    )
    remote = _mk(
        [_comp("COMP-1"), _comp("COMP-2")],
        [_rel("COMP-1", "COMP-2", description="remote")],
    )
    res = three_way_merge(base, local, remote)
    assert len(res.conflicts) == 1
    c = res.conflicts[0]
    assert c.entity_id is None
    assert c.field.startswith("relationship:COMP-1:COMP-2:depends-on.")
    assert c.field.endswith("description")
    assert res.stats["relationships_conflicted"] == 1


def test_relationship_removed_by_one_modified_by_other_conflict():
    rel_base = _rel("COMP-1", "COMP-2", description="orig")
    rel_mod = _rel("COMP-1", "COMP-2", description="modified")
    base = _mk([_comp("COMP-1"), _comp("COMP-2")], [rel_base])
    local = _mk([_comp("COMP-1"), _comp("COMP-2")], [])  # removed
    remote = _mk([_comp("COMP-1"), _comp("COMP-2")], [rel_mod])
    res = three_way_merge(base, local, remote)
    assert len(res.conflicts) == 1
    assert "__removed__" in res.conflicts[0].field
    # Placeholder: keep remote.
    assert len(res.merged_model.relationships) == 1


# ------------------------------------------------------------- meta


def test_meta_schema_version_divergence_conflict():
    base = _mk([_comp("COMP-1")], meta={"schema_version": "2.0"})
    local = _mk([_comp("COMP-1")], meta={"schema_version": "2.1"})
    remote = _mk([_comp("COMP-1")], meta={"schema_version": "2.2"})
    res = three_way_merge(base, local, remote)
    fields = [c.field for c in res.conflicts]
    assert "meta.schema_version" in fields


# ------------------------------------------------------------- multi-category


def test_multi_category_stats_counters():
    base_raw = {
        "meta": {"schema_version": "2.0", "project": "t", "generated_at": "2026-01-01T00:00:00+00:00"},
        "entities": {
            "components": [_comp("COMP-1"), _comp("COMP-2")],
            "capabilities": [{"id": "CAP-1", "name": "K", "status": "ACTIVE"}],
        },
        "relationships": [],
    }
    local_raw = {
        "meta": {"schema_version": "2.0", "project": "t", "generated_at": "2026-01-01T00:00:00+00:00"},
        "entities": {
            "components": [_comp("COMP-1", name="local"), _comp("COMP-2"), _comp("COMP-3")],
            "capabilities": [{"id": "CAP-1", "name": "K", "status": "ACTIVE"}],
        },
        "relationships": [],
    }
    remote_raw = {
        "meta": {"schema_version": "2.0", "project": "t", "generated_at": "2026-01-01T00:00:00+00:00"},
        "entities": {
            "components": [_comp("COMP-1"), _comp("COMP-2")],
            "capabilities": [
                {"id": "CAP-1", "name": "K", "status": "ACTIVE"},
                {"id": "CAP-2", "name": "N", "status": "ACTIVE"},
            ],
        },
        "relationships": [],
    }
    b, l, r = _parse_raw(base_raw), _parse_raw(local_raw), _parse_raw(remote_raw)
    res = three_way_merge(b, l, r)
    assert res.conflicts == []
    assert res.stats["entities_added_local"] == 1
    assert res.stats["entities_added_remote"] == 1
    # COMP-1 has local change → auto-merged; COMP-2 unchanged all around; CAP-1 unchanged.
    assert res.stats["entities_auto_merged"] >= 2


def test_merge_integrity_error_raised_on_parse_failure(monkeypatch):
    def _boom(_raw):
        raise ValueError("synthetic parse failure")

    monkeypatch.setattr(merge_mod, "_parse_raw", _boom)
    base = _mk([_comp("COMP-1")])
    with pytest.raises(MergeIntegrityError) as exc_info:
        three_way_merge(base, base, base)
    assert "synthetic parse failure" in str(exc_info.value)


# ------------------------------------------------------------- determinism


def test_conflict_ordering_deterministic():
    # Two divergent field conflicts on different entities — verify stable order.
    base = _mk([_comp("COMP-A", name="A"), _comp("COMP-B", name="B")])
    local = _mk([_comp("COMP-A", name="AL"), _comp("COMP-B", name="BL")])
    remote = _mk([_comp("COMP-A", name="AR"), _comp("COMP-B", name="BR")])
    res1 = three_way_merge(base, local, remote)
    res2 = three_way_merge(base, local, remote)
    assert res1.conflicts == res2.conflicts
    assert [c.entity_id for c in res1.conflicts] == ["COMP-A", "COMP-B"]


def test_stats_present_even_when_no_activity():
    base = _mk()
    res = three_way_merge(base, base, base)
    expected = {
        "entities_auto_merged",
        "entities_conflicted",
        "entities_added_local",
        "entities_added_remote",
        "relationships_auto_merged",
        "relationships_conflicted",
    }
    assert expected <= set(res.stats)
    assert all(v == 0 for v in res.stats.values())


def test_conflict_dataclass_is_frozen():
    c = Conflict(entity_id="X", field="f", base=1, local=2, remote=3)
    with pytest.raises(Exception):
        c.field = "y"  # type: ignore[misc]


def test_result_dataclass_is_frozen():
    base = _mk()
    res = three_way_merge(base, base, base)
    with pytest.raises(Exception):
        res.conflicts = []  # type: ignore[misc]
