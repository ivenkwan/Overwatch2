"""TASK-011/012: graph pagination + query cache; alert-feed SQL shape."""

import asyncio

import pytest

from app.services import query_cache
from app.services.graph_service import InvalidGraphInput, get_full_network, get_neighborhood


class FakeConn:
    def __init__(self, queries=None):
        self.queries = queries if queries is not None else []

    async def fetch(self, query, *args):
        self.queries.append(query)
        return []


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------- TASK-011

def test_full_network_pagination_in_sql():
    conn = FakeConn()
    run(get_full_network(conn, 50, offset=100))
    # openCypher/AGE requires SKIP before LIMIT (verified live on AGE)
    assert "SKIP 100 LIMIT 50" in conn.queries[0]


def test_full_network_offset_clamped_and_validated():
    conn = FakeConn()
    run(get_full_network(conn, 50, offset=-5))  # negative clamps to 0
    assert "SKIP 0" in conn.queries[0]
    with pytest.raises(InvalidGraphInput):
        run(get_full_network(conn, 50, offset="abc"))
    assert len(conn.queries) == 1  # non-int never reaches the DB


def test_query_cache_hit_and_ttl():
    query_cache.clear()
    calls = []

    async def loader():
        calls.append(1)
        return {"data": "x"}

    first = run(query_cache.cached("ns", loader, ttl=60, k="v"))
    second = run(query_cache.cached("ns", loader, ttl=60, k="v"))
    assert first == second == {"data": "x"}
    assert len(calls) == 1  # second call served from cache


def test_query_cache_never_caches_none():
    query_cache.clear()
    calls = []

    async def loader():
        calls.append(1)
        return None

    run(query_cache.cached("ns2", loader, k="v"))
    run(query_cache.cached("ns2", loader, k="v"))
    assert len(calls) == 2  # None results always reload


def test_query_cache_expiry():
    query_cache.clear()
    query_cache.put("exp", "val", ttl=0, k="x")  # ttl 0 expires immediately
    assert query_cache.get("exp", k="x") is None


def test_query_cache_clear_namespace():
    query_cache.clear()
    query_cache.put("a", 1, k="1")
    query_cache.put("b", 2, k="1")
    assert query_cache.clear("a") == 1
    assert query_cache.get("a", k="1") is None
    assert query_cache.get("b", k="1") == 2
    query_cache.clear()


# ---------------------------------------------------------------- TASK-012

def test_alert_feed_filters_are_server_side():
    """The feed query must carry the filters in SQL (bind params), never
    paginate client-side."""
    import pathlib
    source = pathlib.Path(
        "/home/ivenkwan/repo/Overwatch2/aml_platform/backend/app/api/v1/alerts.py").read_text()
    assert "txn_amount_in_hkd >= $1" in source
    assert "txn_type = $2" in source
    assert "$3" in source  # limit bound too


def test_alert_feed_cache_headers_present():
    import pathlib
    source = pathlib.Path(
        "/home/ivenkwan/repo/Overwatch2/aml_platform/backend/app/api/v1/alerts.py").read_text()
    assert 'Cache-Control' in source and 'max-age=5' in source


def test_feed_indexes_migration_present():
    import pathlib
    sql = pathlib.Path(
        "/home/ivenkwan/repo/Overwatch2/aml_platform/backend/init_scripts/06_alert_feed_indexes.sql"
    ).read_text()
    assert "idx_core_transactions_txn_date" in sql
    assert "idx_core_transactions_type_date" in sql
    assert "idx_app_alerts_status_created" in sql
