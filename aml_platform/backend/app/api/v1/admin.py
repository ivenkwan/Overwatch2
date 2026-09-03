from fastapi import APIRouter, Depends, HTTPException, Header, Body
from typing import List, Optional
from pydantic import BaseModel
from keycloak import KeycloakAdmin
import asyncpg
from app.core import auth
from app.core.config import get_settings
from app.db.session import get_db
from app.services import audit_service

router = APIRouter()

class UserCreate(BaseModel):
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: str

class RoleAssign(BaseModel):
    role_code: str

def get_keycloak_admin():
    # Admin credentials come exclusively from the environment (no defaults —
    # the former admin/admin fallback is removed).
    settings = get_settings()
    if not settings.keycloak_admin_user or not settings.keycloak_admin_password:
        raise HTTPException(
            status_code=503,
            detail="Keycloak admin credentials not configured (KEYCLOAK_ADMIN_USER / KEYCLOAK_ADMIN_PASSWORD)",
        )
    try:
        return KeycloakAdmin(
            server_url=settings.keycloak_url + "/",
            username=settings.keycloak_admin_user,
            password=settings.keycloak_admin_password,
            realm_name=settings.keycloak_admin_realm,
            verify=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to connect to Keycloak")

@router.post("/users", status_code=201)
async def create_user(
    new_user: UserCreate,
    x_tenant_id: str = Header(..., description="Tenant ID executing the addition"),
    current_user: dict = Depends(auth.require_role("ADMIN")),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Provisions a user in Keycloak and maps them to the local `app_users` table 
    and hooks them into the executing `tenant`.
    """
    keycloak_admin = get_keycloak_admin()
    
    # 1. Provision user in Keycloak
    try:
        new_user_payload = {
            "username": new_user.username,
            "email": new_user.email,
            "firstName": new_user.first_name,
            "lastName": new_user.last_name,
            "enabled": True,
            "credentials": [{"value": new_user.password, "type": "password", "temporary": False}]
        }
        keycloak_user_id = keycloak_admin.create_user(new_user_payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Keycloak provisioning failed: {str(e)}")

    # 2. Local Database Sync: Sync to app_users and tenant_memberships
    full_name = f"{new_user.first_name or ''} {new_user.last_name or ''}".strip()
    
    async with conn.transaction():
        # Insert or grab existing user mapping
        user_record = await conn.fetchrow(
            """
            INSERT INTO app.app_users (keycloak_user_id, username, email, full_name)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (keycloak_user_id) DO UPDATE SET email = EXCLUDED.email
            RETURNING user_id;
            """,
            keycloak_user_id, 
            new_user.username, 
            new_user.email, 
            full_name
        )
        
        # Insert tenant membership
        try:
            await conn.execute(
                """
                INSERT INTO app.tenant_memberships (tenant_id, user_id, membership_status)
                VALUES ($1, $2, 'active')
                ON CONFLICT DO NOTHING;
                """,
                x_tenant_id,
                user_record["user_id"]
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Database synchronization failed: {str(e)}")

    await audit_service.record_audit_event(
        "USER_CREATED",
        actor=current_user,
        resource_type="USER",
        resource_id=str(user_record["user_id"]),
        reason=f"username={new_user.username} tenant={x_tenant_id} keycloak_user={keycloak_user_id}",
        tenant_id=x_tenant_id,
        db=conn,
    )
    return {
        "status": "success",
        "message": "User provisioned and mapped locally.",
        "keycloak_user_id": keycloak_user_id,
        "local_user_id": str(user_record["user_id"])
    }

@router.get("/users")
async def get_tenant_users(
    x_tenant_id: str = Header(..., description="Tenant ID executing the request"),
    current_user: dict = Depends(auth.require_role("ADMIN")),
    conn: asyncpg.Connection = Depends(get_db)
):
    """Get all users mapped to the current tenant."""
    users = await conn.fetch(
        """
        SELECT u.user_id, u.username, u.email, u.full_name, u.status, m.joined_at
        FROM app.app_users u
        JOIN app.tenant_memberships m ON u.user_id = m.user_id
        WHERE m.tenant_id = $1
        """,
        x_tenant_id
    )
    return {"status": "success", "users": [dict(u) for u in users]}

@router.get("/roles")
async def get_roles(
    current_user: dict = Depends(auth.require_role("ADMIN")),
    conn: asyncpg.Connection = Depends(get_db)
):
    """Fetch predefined roles that an admin can assign to a user."""
    roles = await conn.fetch("SELECT role_id, role_code, role_name, description FROM app.roles WHERE role_scope = 'tenant';")
    return {"status": "success", "roles": [dict(r) for r in roles]}

@router.post("/users/{local_user_id}/roles")
async def assign_role(
    local_user_id: str,
    payload: RoleAssign,
    x_tenant_id: str = Header(..., description="Tenant ID executing the addition"),
    current_user: dict = Depends(auth.require_role("ADMIN")),
    conn: asyncpg.Connection = Depends(get_db)
):
    """Map a role to a user internally."""
    async with conn.transaction():
        # Resolve role ID
        role_record = await conn.fetchrow("SELECT role_id FROM app.roles WHERE role_code = $1 AND role_scope = 'tenant'", payload.role_code)
        if not role_record:
            raise HTTPException(status_code=404, detail="Role not found")
            
        role_id = role_record['role_id']
        
        # Ensure user is in tenant
        member = await conn.fetchrow("SELECT 1 FROM app.tenant_memberships WHERE tenant_id = $1 AND user_id = $2", x_tenant_id, local_user_id)
        if not member:
            raise HTTPException(status_code=403, detail="User is not a member of this tenant")
            
        await conn.execute(
            """
            INSERT INTO app.user_tenant_roles (tenant_id, user_id, role_id) 
            VALUES ($1, $2, $3)
            ON CONFLICT DO NOTHING;
            """,
            x_tenant_id, local_user_id, role_id
        )
        
    await audit_service.record_audit_event(
        "ROLE_ASSIGNED",
        actor=current_user,
        resource_type="USER",
        resource_id=local_user_id,
        reason=f"role={payload.role_code} tenant={x_tenant_id}",
        db=conn,
    )
    return {"status": "success", "message": f"Role '{payload.role_code}' assigned to user."}
