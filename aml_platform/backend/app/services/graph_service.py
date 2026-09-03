"""
Apache AGE graph queries (TASK-003 hardening).

Constraint: with asyncpg, a Cypher query must be passed to cypher() as one
dollar-quoted SQL string, so bind parameters ($1, $2, ...) cannot be placed
inside the Cypher body. Injection is therefore prevented by construction:

  1. `limit` and `depth` are coerced to int and clamped server-side — they
     can only ever render as bounded integer literals.
  2. `entity_id` must pass a strict allowlist (validate_entity_id): a short,
     fixed charset and a hard length cap. Values that could terminate the
     dollar-quoted block or quote out of a string (quotes, backslashes,
     dollar signs, semicolons, whitespace, unicode) are rejected outright.
  3. As defence-in-depth the id is additionally escaped (escape_cypher_string)
     before embedding.

Every query in this module builds its Cypher body exclusively from these
validated values.
"""

import json
import re

# Identifiers used in the graph: customer numbers, wallet addresses
# (0x-hex), txn hashes, account ids like ACC_SUSPECT_01. Colon is included
# for namespaced ids (e.g. "ETHEREUM:0xabc").
ENTITY_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:@-]{1,128}$")

MAX_LIMIT = 500
MAX_DEPTH = 6


class InvalidGraphInput(ValueError):
    """Raised when a graph query parameter fails allowlist validation."""


def clamp_limit(limit) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        raise InvalidGraphInput("limit must be an integer")
    return max(1, min(value, MAX_LIMIT))


def clamp_depth(depth) -> int:
    try:
        value = int(depth)
    except (TypeError, ValueError):
        raise InvalidGraphInput("depth must be an integer")
    return max(1, min(value, MAX_DEPTH))


def validate_entity_id(entity_id) -> str:
    """Allowlist entity identifiers; anything else is rejected (400 upstream)."""
    value = str(entity_id) if entity_id is not None else ""
    if not value or len(value) > 128 or not ENTITY_ID_PATTERN.match(value):
        raise InvalidGraphInput(
            "Invalid entity id: only letters, digits, '.', '_', '-', ':', '@' "
            "allowed (max 128 chars)"
        )
    return value


def escape_cypher_string(value: str) -> str:
    """Escape a value for a single-quoted Cypher string literal.

    Only reached after allowlist validation; belt-and-braces for both the
    Cypher string literal and the surrounding SQL dollar-quote.
    """
    return value.replace("\\", "\\\\").replace("'", "''")


def _parse_prop(raw):
    try:
        return json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        return {}


def _row_to_elements(r, elements: list, seen_nodes: set) -> None:
    n_prop = _parse_prop(r["n_prop"])
    m_prop = _parse_prop(r["m_prop"])
    n_id = str(r["n_id"])
    m_id = str(r["m_id"])

    if n_id not in seen_nodes:
        elements.append({"data": {**n_prop, "id": n_id, "label": str(r["n_lbl"]).strip('"')}})
        seen_nodes.add(n_id)

    if m_id not in seen_nodes:
        elements.append({"data": {**m_prop, "id": m_id, "label": str(r["m_lbl"]).strip('"')}})
        seen_nodes.add(m_id)

    r_prop = _parse_prop(r["r_prop"])
    elements.append({
        "data": {
            "id": f"edge_{r['r_id']}",
            "source": n_id,
            "target": m_id,
            "label": str(r["r_lbl"]).strip('"'),
            **r_prop,
        }
    })


async def get_full_network(db, limit, offset: int = 0) -> list:
    limit = clamp_limit(limit)
    try:
        offset = max(0, int(offset))
    except (TypeError, ValueError):
        raise InvalidGraphInput("offset must be an integer")

    # openCypher pagination order: SKIP before LIMIT (verified live on AGE).
    query = f"""
    SELECT * FROM cypher('tap_and_go_network', $$
        MATCH (n)-[r]->(m)
        RETURN properties(n), id(n), label(n), properties(r), id(r), label(r), properties(m), id(m), label(m)
        SKIP {offset} LIMIT {limit}
    $$) AS (n_prop agtype, n_id agtype, n_lbl agtype, r_prop agtype, r_id agtype, r_lbl agtype, m_prop agtype, m_id agtype, m_lbl agtype);
    """

    rows = await db.fetch(query)
    elements: list = []
    seen_nodes: set = set()
    for r in rows:
        _row_to_elements(r, elements, seen_nodes)
    return elements


async def get_neighborhood(db, entity_id, depth) -> list:
    """Fetches a subgraph centered around entity_id up to 'depth' hops away."""
    entity_id_clean = escape_cypher_string(validate_entity_id(entity_id))
    depth_clean = clamp_depth(depth)

    query = f"""
    SELECT * FROM cypher('tap_and_go_network', $$
        MATCH path=(root {{id: '{entity_id_clean}'}})-[*1..{depth_clean}]-(m)
        UNWIND relationships(path) AS rel
        WITH DISTINCT rel
        RETURN properties(startNode(rel)), id(startNode(rel)), label(startNode(rel)),
               properties(rel), id(rel), label(rel),
               properties(endNode(rel)), id(endNode(rel)), label(endNode(rel))
    $$) AS (n_prop agtype, n_id agtype, n_lbl agtype, r_prop agtype, r_id agtype, r_lbl agtype, m_prop agtype, m_id agtype, m_lbl agtype);
    """

    rows = await db.fetch(query)
    elements: list = []
    seen_nodes: set = set()
    for r in rows:
        _row_to_elements(r, elements, seen_nodes)
    return elements
