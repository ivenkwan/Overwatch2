import os
import asyncpg
from typing import AsyncGenerator

# Point to the container age_db if inside Docker, or localhost:5432 if running on host.
# Note: Changing to the aml_api_role as per the new RBAC structure.
database_url = os.environ.get("DATABASE_URL", "postgresql://aml_api_role:aml_secure_api_password@localhost:5432/age_prod_01")

class DatabaseState:
    pool: asyncpg.Pool = None

db_state = DatabaseState()

async def init_connection(conn):
    await conn.execute("LOAD 'age';")
    await conn.execute("SET search_path = ag_catalog, \"$user\", public;")

async def init_db_pool():
    db_state.pool = await asyncpg.create_pool(
        dsn=database_url,
        min_size=2,
        max_size=20,
        setup=init_connection
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
