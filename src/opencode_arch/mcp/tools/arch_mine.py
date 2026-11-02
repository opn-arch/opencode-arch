"""``arch_mine`` — openAG reservoir-mining pass (openAG-native).

Mirrors ``openag.mcp.tools.mine_tool`` behind the OCA envelope. Reads
opencode session chunks from a sessions SQLite DB, scopes them to the
real tributary repos actually present in the DB, and runs the single
``extract → propagate → reservoir`` path (``openag.mining.runner.mine_run``)
over the openAG model graph. PROPOSED promise records are appended to the
``reservoir`` JSONL and processed sources are recorded in the ``ledger``
so reruns are idempotent.

The LLM provider is injected via the optional ``provider`` param so tests
stay offline/deterministic; production constructs one via ``make_provider``.
The openAG model lives at ``<repo_path>/.architecture/model/`` as a
directory of ``*.v3.yaml`` fragments, loaded via ``_openag_loader``.
"""
from __future__ import annotations

from opencode_arch.mcp._arch_tool import arch_tool
from opencode_arch.mcp.tools._openag_loader import build_graph, load_doc


@arch_tool
async def arch_mine(
    repo_path: str = "",
    *,
    db: str = "",
    reservoir: str = "",
    ledger: str = "",
    repo: str | None = None,
    session: str | None = None,
    model: str | None = None,
    provider=None,
) -> dict:
    """Run the reservoir-mining pass over opencode sessions.

    ``db``, ``reservoir``, and ``ledger`` are required. When ``provider``
    is ``None`` a real provider is constructed via ``make_provider`` (tests
    inject a deterministic stub). ``repo`` / ``session`` narrow the mined
    chunks to a single repo slug / session id.
    """
    if not db or not reservoir or not ledger:
        raise ValueError("db, reservoir, and ledger are required")

    import os
    import sqlite3

    from openag.mining.runner import mine_run
    from openag.mining.sources import iter_chunks, resolve_scope

    doc = load_doc(repo_path)
    g = build_graph(doc)

    con = sqlite3.connect(db)
    try:
        present = {
            os.path.basename((row[0] or "").rstrip("/"))
            for row in con.execute("SELECT worktree FROM project")
        }
    finally:
        con.close()

    scope = resolve_scope(present)
    chunks = [
        c
        for c in iter_chunks(db, allowed_repos=scope)
        if (repo is None or c.repo == repo)
        and (session is None or c.session_id == session)
    ]

    prov = provider
    if prov is None:
        from openag.kernel.provider_factory import make_provider

        prov = make_provider(model=model)

    return mine_run(
        chunks, g, prov, reservoir_path=reservoir, ledger_path=ledger
    )


__all__ = ["arch_mine"]
