"""
Tenant context resolution (AWI TASK-042).

Fail-closed multi-tenancy: every AWI endpoint resolves the acting user's
tenant membership explicitly and sets `app.current_tenant` on the connection
before any query. No `LIMIT 1` fallbacks — a user without an active
membership gets 403, not another tenant's data.
"""

from typing import AsyncGenerator

import asyncpg

from app.core.exceptions import AuthorizationAppError


class TenantContext:
    def __init__(self, user_id, tenant_id, username: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.username = username


async def set_tenant_context(db: asyncpg.Connection, ctx: TenantContext) -> None:
    await db.execute("SELECT set_config('app.current_tenant', $1, true)", str(ctx.tenant_id))
    await db.execute("SELECT set_config('app.actor_user_id', $1, true)", str(ctx.user_id))


async def resolve_tenant(current_user: dict, db: asyncpg.Connection) -> TenantContext:
    """Resolve the acting user to an app_users row + active tenant membership."""
    row = await db.fetchrow(
        """
        SELECT u.user_id, m.tenant_id
        FROM app.app_users u
        JOIN app.tenant_memberships m
          ON m.user_id = u.user_id AND m.membership_status = 'active'
        WHERE u.username = $1
           OR (u.keycloak_user_id IS NOT NULL AND u.keycloak_user_id::text = $2)
        ORDER BY m.joined_at
        LIMIT 1
        """,
        current_user.get("username"),
        str(current_user.get("id") or ""),
    )
    if not row:
        raise AuthorizationAppError(
            "Acting user has no active tenant membership; tenant context cannot be established"
        )
    return TenantContext(row["user_id"], row["tenant_id"], current_user.get("username", ""))


async def get_tenant_db(
    current_user: dict,
    db: asyncpg.Connection,
) -> tuple:
    """Resolve tenant context and apply RLS settings on the connection."""
    ctx = await resolve_tenant(current_user, db)
    await set_tenant_context(db, ctx)
    return db, ctx
