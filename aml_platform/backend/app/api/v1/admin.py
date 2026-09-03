from fastapi import APIRouter, Depends, HTTPException, Header, Body
from typing import List, Optional
from pydantic import BaseModel
from keycloak import KeycloakAdmin
import os
import asyncpg
from app.db.session import get_db

# Initialize Keycloak Admin configuration from environment
KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "http://host.docker.internal:8080")
KEYCLOAK_ADMIN_USER = os.environ.get("KEYCLOAK_ADMIN_USER", "admin")
KEYCLOAK_ADMIN_PASSWORD = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "admin")
KEYCLOAK_REALM_NAME = os.environ.get("KEYCLOAK_REALM_NAME", "master")

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
    try:
        return KeycloakAdmin(
            server_url=KEYCLOAK_URL,
            username=KEYCLOAK_ADMIN_USER,
            password=KEYCLOAK_ADMIN_PASSWORD,
            realm_name=KEYCLOAK_REALM_NAME,
            verify=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to Keycloak: {str(e)}")

@router.post("/users", status_code=201)
async def create_user(
    new_user: UserCreate, 
    x_tenant_id: str = Header(..., description="Tenant ID executing the addition"),
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

    return {
        "status": "success",
        "message": "User provisioned and mapped locally.",
        "keycloak_user_id": keycloak_user_id,
        "local_user_id": str(user_record["user_id"])
    }

@router.get("/users")
async def get_tenant_users(
    x_tenant_id: str = Header(..., description="Tenant ID executing the request"),
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
async def get_roles(conn: asyncpg.Connection = Depends(get_db)):
    """Fetch predefined roles that an admin can assign to a user."""
    roles = await conn.fetch("SELECT role_id, role_code, role_name, description FROM app.roles WHERE role_scope = 'tenant';")
    return {"status": "success", "roles": [dict(r) for r in roles]}

@router.post("/users/{local_user_id}/roles")
async def assign_role(
    local_user_id: str,
    payload: RoleAssign,
    x_tenant_id: str = Header(..., description="Tenant ID executing the addition"),
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
        
    return {"status": "success", "message": f"Role '{payload.role_code}' assigned to user."}
