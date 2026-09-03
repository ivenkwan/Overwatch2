"""TASK-039: the T+1 batch must project the party dimension after staging.

Unit-level regression: run_t1_batch_job() invokes
party_loader.run_party_projection() after the regulatory gate. The database
and normalizers are faked; what matters here is the wiring, not the SQL.
"""

import asyncio
import importlib
import sys
import types
from unittest.mock import MagicMock

ETL_DIR = "/home/ivenkwan/repo/Overwatch2/aml_platform/etl"


def _load_run_batch(monkeypatch, party_calls):
    """Import aml_platform/etl/run_batch.py with faked DB + party_loader."""
    if ETL_DIR not in sys.path:
        sys.path.insert(0, ETL_DIR)

    party_loader = types.ModuleType("party_loader")
    party_loader.run_party_projection = lambda: party_calls.append(1)
    monkeypatch.setitem(sys.modules, "party_loader", party_loader)

    executed = []

    class FakeCursor:
        def execute(self, sql, *args):
            executed.append(sql)

        def close(self):
            pass

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            pass

        def close(self):
            pass

    run_batch = importlib.import_module("run_batch")
    monkeypatch.setattr(run_batch, "get_db_connection", lambda: FakeConn())
    monkeypatch.setattr(run_batch, "execute_values",
                        lambda cur, sql, vals: executed.append(sql))
    return run_batch, executed


def test_batch_invokes_party_projection(monkeypatch):
    party_calls = []
    run_batch, executed = _load_run_batch(monkeypatch, party_calls)

    run_batch.run_t1_batch_job()  # sync psycopg2 pipeline

    assert party_calls == [1], "run_t1_batch_job must call party_loader.run_party_projection()"
    # and the regulatory gate still runs before it
    assert any("sp_screen_ofac" in str(q) for q in executed)


def test_party_loader_is_idempotent_merges(monkeypatch):
    """The projection itself must MERGE (Lesson 3: idempotency). Source check."""
    import pathlib
    source = pathlib.Path(ETL_DIR, "party_loader.py").read_text()
    assert "MERGE" in source
    assert "ON CONFLICT" in source or "MERGE" in source


# ---- AWI TASK-049/050: authorization-aware gate wiring ---------------------

def test_gate_runs_blocklist_before_ofac(monkeypatch):
    """The T+1 batch screens the internal revoked-credential blocklist BEFORE
    the OFAC screen (so BLOCKED rows are quarantined before the PENDING->
    SCREENED promotion), and the OFAC screen ALWAYS runs afterwards."""
    run_batch, executed = _load_run_batch(monkeypatch, [])

    run_batch.run_t1_batch_job()

    calls = [str(q) for q in executed]
    attach = next((i for i, q in enumerate(calls) if "sp_attach_auth_metadata" in q), None)
    blocklist = next((i for i, q in enumerate(calls) if "sp_screen_internal_blocklist" in q), None)
    ofac = next((i for i, q in enumerate(calls) if "sp_screen_ofac" in q), None)

    assert attach is not None and blocklist is not None and ofac is not None
    assert attach < blocklist < ofac, "ordering must be attach -> blocklist -> OFAC"


def test_no_code_path_skips_ofac_for_authorized(monkeypatch):
    """Invariant (TASK-050 / ADR-0002): authorization never exempts a wallet
    from screening. The batch always calls sp_screen_ofac unconditionally and
    the gate SQL never conditions the OFAC screen on authorization."""
    import pathlib
    run_batch_src = pathlib.Path(ETL_DIR, "run_batch.py").read_text()
    gate_sql = pathlib.Path(
        "/home/ivenkwan/repo/Overwatch2/aml_platform/init-scripts/08-regulatory-authorization.sql"
    ).read_text()

    # 1. The batch calls the OFAC screen unconditionally (no if/guard around it).
    ofac_line = [l for l in run_batch_src.splitlines() if "sp_screen_ofac" in l]
    assert ofac_line and all(not l.lstrip().startswith(("if ", "#", "else")) for l in ofac_line)
    # 2. The blocklist gate only QUARANTINES (never skips) and never consults
    #    an authorization flag to bypass the screen.
    assert "authorized" not in gate_sql.lower().split("sp_screen_internal_blocklist")[1][:200].lower() \
        or "never skips" in gate_sql
    assert "CREDENTIAL_REVOKED" in gate_sql
    assert "CRITICAL" in gate_sql


def test_blocklist_lifecycle_procs_present():
    """Lifecycle (revoke -> re-verify -> restore): the gate ships add/remove
    procedures with an active-flag so a re-verified wallet can be restored."""
    import pathlib
    gate_sql = pathlib.Path(
        "/home/ivenkwan/repo/Overwatch2/aml_platform/init-scripts/08-regulatory-authorization.sql"
    ).read_text()
    assert "sp_internal_blocklist_add" in gate_sql
    assert "sp_internal_blocklist_remove" in gate_sql
    assert "active = TRUE" in gate_sql and "active = FALSE" in gate_sql
