"""
Database access layer for the tamper-evident audit trail (TASK-004).

All SQL here is static, module-level text executed exclusively with asyncpg
bind parameters ($1, $2, ...) — asyncpg's placeholder syntax. No user input
is ever interpolated into SQL text; every parameter is normalised to a typed
value (uuid.UUID or str) before reaching this module.
"""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

_INSERT_EVENT_SQL = """
    INSERT INTO app.audit_access_events
        (tenant_id, user_id, resource_type, resource_id, action, decision, reason)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    RETURNING event_id
"""

_RESOLVE_USER_SQL = """
    SELECT user_id FROM app.app_users WHERE keycloak_user_id = $1
"""

_FETCH_EVENTS_SQL = """
    SELECT event_id, tenant_id, user_id, resource_type, resource_id,
           action, decision, reason, created_at, previous_hash, record_hash
    FROM app.audit_access_events
    WHERE created_at >= COALESCE($1::timestamptz, '-infinity'::timestamptz)
      AND created_at <= COALESCE($2::timestamptz, 'infinity'::timestamptz)
    ORDER BY created_at DESC
    LIMIT $3
"""

# Recomputes the trigger-built hash chain entirely inside PostgreSQL so the
# text representation of timestamptz matches app.hash_audit_event exactly.
_VERIFY_CHAIN_SQL = """
    WITH ordered AS (
        SELECT *, LAG(record_hash) OVER (ORDER BY created_at, event_id) AS prev_hash
        FROM app.audit_access_events
    ), recomputed AS (
        SELECT *,
            COALESCE(prev_hash, 'genesis') AS expected_prev,
            encode(digest(
                COALESCE(prev_hash, 'genesis')
                || COALESCE(tenant_id::TEXT, '')
                || COALESCE(user_id::TEXT, '')
                || resource_type
                || COALESCE(resource_id::TEXT, '')
                || action
                || decision
                || COALESCE(reason, '')
                || created_at::TEXT,
                'sha256'), 'hex') AS expected_hash
        FROM ordered
    )
    SELECT
        COUNT(*)::INT AS total,
        COUNT(*) FILTER (
            WHERE previous_hash <> expected_prev OR record_hash <> expected_hash
        )::INT AS broken,
        MIN(created_at) FILTER (
            WHERE previous_hash <> expected_prev OR record_hash <> expected_hash
        ) AS broken_at
    FROM recomputed
"""

UuidOrNone = Optional[uuid.UUID]


def to_uuid(value) -> UuidOrNone:
    """Normalise any value to a uuid.UUID if it is a valid UUID, else None."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


@asynccontextmanager
async def _connection(db=None):
    """Yield a database connection, acquiring one from the pool if needed."""
    if db is not None and not hasattr(db, "acquire"):
        yield db
        return
    from app.db.session import db_state

    if db_state.pool is None:
        raise RuntimeError("Database pool not initialised")
    async with db_state.pool.acquire() as conn:
        yield conn


async def insert_audit_event(
    db,
    tenant_id: UuidOrNone,
    user_id: UuidOrNone,
    resource_type: str,
    resource_id: UuidOrNone,
    action: str,
    decision: str,
    reason: Optional[str],
) -> Optional[uuid.UUID]:
    """Append one event to the hash-chained audit table; returns its event_id."""
    async with _connection(db) as conn:
        row = await conn.fetchrow(
            _INSERT_EVENT_SQL,
            tenant_id,
            user_id,
            resource_type,
            resource_id,
            action,
            decision,
            reason,
        )
    return row["event_id"] if row else None


async def resolve_local_user_id(db, keycloak_subject: str) -> UuidOrNone:
    """Map a Keycloak subject UUID to the local app.app_users user_id."""
    sub = to_uuid(keycloak_subject)
    if sub is None:
        return None
    try:
        async with _connection(db) as conn:
            row = await conn.fetchrow(_RESOLVE_USER_SQL, str(sub))
        return to_uuid(row["user_id"]) if row else None
    except Exception:
        return None


async def fetch_audit_events(
    db,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = 1000,
) -> list:
    """Read audit events (most recent first) for export or review."""
    limit = max(1, min(int(limit), 10000))
    async with _connection(db) as conn:
        rows = await conn.fetch(_FETCH_EVENTS_SQL, since, until, limit)
    return [dict(r) for r in rows]


async def verify_audit_chain(db) -> dict:
    """Recompute the SHA-256 hash chain in SQL and report integrity status.

    Mirrors app.hash_audit_event(): each record_hash must equal
    sha256(previous_hash || tenant_id || user_id || resource_type ||
    resource_id || action || decision || reason || created_at), where
    previous_hash chains to the preceding row (genesis for the first row).
    """
    async with _connection(db) as conn:
        row = await conn.fetchrow(_VERIFY_CHAIN_SQL)
    total = row["total"] or 0
    broken = row["broken"] or 0
    return {
        "valid": broken == 0,
        "checked": total,
        "broken_records": broken,
        "broken_at": row["broken_at"].isoformat() if row["broken_at"] else None,
        "detail": "chain intact" if broken == 0 else "hash chain mismatch — records may have been tampered with",
    }
