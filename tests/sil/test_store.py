def test_store_emit_writes_row_and_trims_to_50(tmp_path):
    from opencode_arch.sil.store import SILStore
    s = SILStore(tmp_path / "sil.sqlite")
    for i in range(60):
        s.emit("stage:x", "invocation", "ok", 10)
    rows = s.recent("stage:x")
    assert len(rows) == 50


def test_store_error_outcome_recorded():
    from opencode_arch.sil.store import SILStore
    s = SILStore(":memory:")
    s.emit("stage:x", "invocation", "error", 5, ref="ValueError")
    rows = s.recent("stage:x")
    assert rows[0]["outcome"] == "error"
    assert rows[0]["ref"] == "ValueError"
