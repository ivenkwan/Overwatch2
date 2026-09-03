import os
import asyncpg
from typing import AsyncGenerator

from app.core.config import get_settings

# The DSN (including credentials) must come from the environment — there is
# deliberately no in-code fallback (TASK-001: no hardcoded secrets).
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL environment variable is required "
        "(e.g. postgresql://user:password@host:5432/age_prod_01)"
    )

class DatabaseState:
    pool: asyncpg.Pool = None

db_state = DatabaseState()

async def init_connection(conn):
    await conn.execute("LOAD 'age';")
    await conn.execute("SET search_path = ag_catalog, \"$user\", public;")

async def init_db_pool():
    """Create the connection pool (TASK-008: sizes, timeouts from environment).

    - DB_POOL_MIN / DB_POOL_MAX          pool bounds
    - DB_QUERY_TIMEOUT_MS                server-side statement_timeout guard
    - DB_ACQUIRE_TIMEOUT_S               max wait for a free connection
    """
    settings = get_settings()
    db_state.pool = await asyncpg.create_pool(
        dsn=database_url,
        min_size=settings.db_pool_min,
        max_size=settings.db_pool_max,
        timeout=settings.db_acquire_timeout_s,
        setup=init_connection,
        server_settings={
            "statement_timeout": str(settings.db_query_timeout_ms),
            "application_name": "aml-backend",
        },
    )

async def close_db_pool():
    if db_state.pool is not None:
        await db_state.pool.close()

async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """Dependency injection wrapper yielding an asyncpg connection from the pool."""
    if db_state.pool is None:
        raise RuntimeError("Database pool has not been initialized.")

    async with db_state.pool.acquire() as conn:
        yield conn

async def db_health() -> dict:
    """Pool status for the /health endpoint (never raises)."""
    pool = db_state.pool
    if pool is None:
        return {"status": "not_initialized"}
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {
            "status": "ok",
            "pool_size": pool.get_size(),
            "pool_idle": pool.get_idle_size(),
            "max_size": pool.get_max_size(),
        }
    except Exception as exc:
        return {"status": "unreachable", "detail": type(exc).__name__}
