"""TASK-003: graph query input hardening (allowlist + clamps + escaping)."""

import asyncio

import pytest

from app.services import graph_service
from app.services.graph_service import (
    InvalidGraphInput,
    clamp_depth,
    clamp_limit,
    escape_cypher_string,
    validate_entity_id,
)


class FakeConn:
    """Captures the SQL text sent to the database."""

    def __init__(self):
        self.queries = []

    async def fetch(self, query, *args):
        self.queries.append(query)
        return []


VALID_IDS = [
    "0xAb5601fD25D887B1d8aE8d0B2F5e9C3aD7412e6B",
    "CUST-001",
    "ACC_SUSPECT_01",
    "ETHEREUM:0xabc123",
    "user_42",
    "a" * 128,
]

INJECTION_PAYLOADS = [
    "$$) AS (x agtype); --",            # dollar-quote termination breakout
    "')} UNION SELECT * FROM app.app_users; --",
    "x' OR '1'='1",
    "x'; DROP TABLE app.audit_access_events; --",
    "x\\",                               # backslash escape
    "x $$ y",                            # dollar signs / whitespace
    "id with spaces",
    "id;semicolon",
    "quote'injection",
    "unicode-é中文",
    "<script>alert(1)</script>",
    "",
    "a" * 129,                           # over length cap
]


@pytest.mark.parametrize("value", VALID_IDS)
def test_valid_entity_ids_accepted(value):
    assert validate_entity_id(value) == value


@pytest.mark.parametrize("value", INJECTION_PAYLOADS)
def test_injection_payloads_rejected(value):
    with pytest.raises(InvalidGraphInput):
        validate_entity_id(value)


def test_none_rejected():
    with pytest.raises(InvalidGraphInput):
        validate_entity_id(None)


def test_limit_clamped():
    assert clamp_limit(10) == 10
    assert clamp_limit(0) == 1
    assert clamp_limit(-5) == 1
    assert clamp_limit(99999) == 500
    with pytest.raises(InvalidGraphInput):
        clamp_limit("150; DROP TABLE x")


def test_depth_clamped():
    assert clamp_depth(3) == 3
    assert clamp_depth(0) == 1
    assert clamp_depth(99) == 6
    with pytest.raises(InvalidGraphInput):
        clamp_depth("2 OR 1=1")


def test_escape_cypher_string():
    assert escape_cypher_string("plain") == "plain"
    assert escape_cypher_string("it's") == "it''s"
    assert escape_cypher_string("back\\slash") == "back\\\\slash"


def test_neighborhood_query_contains_only_validated_id():
    conn = FakeConn()
    validated = validate_entity_id("CUST-001")
    asyncio.run(graph_service.get_neighborhood(conn, validated, 2))
    assert len(conn.queries) == 1
    assert "CUST-001" in conn.queries[0]
    assert "$$" not in conn.queries[0].replace("$$", "", 2)  # only the two dollar-quote fences


def test_neighborhood_rejects_payload_before_db():
    conn = FakeConn()
    with pytest.raises(InvalidGraphInput):
        asyncio.run(graph_service.get_neighborhood(conn, "$$) AS (x agtype); --", 2))
    assert conn.queries == []


def test_full_network_rejects_string_limit():
    conn = FakeConn()
    with pytest.raises(InvalidGraphInput):
        asyncio.run(graph_service.get_full_network(conn, "5 OR 1=1"))
    assert conn.queries == []
