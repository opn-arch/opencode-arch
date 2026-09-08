"""B2.1.5 — snapshot writer serializes SILStore state as YAML."""

from __future__ import annotations


def test_snapshot_writes_yaml_matches_sqlite(tmp_path):
    from opencode_arch.sil.store import SILStore
    from opencode_arch.sil.snapshot import write_snapshot

    s = SILStore(tmp_path / "s.db")
    for _ in range(5):
        s.emit("stage:observe", "invocation", "ok", 10)
    out = tmp_path / "sil" / "stage:observe.yaml"
    write_snapshot(s, "stage:observe", out)
    text = out.read_text()
    assert "component_id: stage:observe" in text
    assert "recent_events:" in text
