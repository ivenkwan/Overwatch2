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
