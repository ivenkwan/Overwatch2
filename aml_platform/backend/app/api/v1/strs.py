# aml_platform/backend/app/api/v1/strs.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
import asyncpg
from app.db.session import get_db
from app.core import auth
from app.schemas.str_schema import STRCreate, STRUpdate, STRResponse

router = APIRouter()

async def get_user_and_tenant(current_user: dict, db: asyncpg.Connection):
    """Helper to resolve DB user_id and tenant_id from username, with fallbacks."""
    user_row = await db.fetchrow(
        "SELECT user_id FROM app.app_users WHERE username = $1", 
        current_user["username"]
    )
    if user_row:
        user_id = user_row["user_id"]
    else:
        user_id = await db.fetchval("SELECT user_id FROM app.app_users LIMIT 1")

    tenant_id = await db.fetchval(
        "SELECT tenant_id FROM app.tenant_memberships WHERE user_id = $1", 
        user_id
    )
    if not tenant_id:
        tenant_id = await db.fetchval("SELECT tenant_id FROM app.tenants LIMIT 1")

    return user_id, tenant_id

@router.post("/", response_model=STRResponse, status_code=status.HTTP_201_CREATED)
async def create_str_draft(
    payload: STRCreate,
    current_user: dict = Depends(auth.get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """
    Initialize a new STR draft.
    """
    user_id, tenant_id = await get_user_and_tenant(current_user, db)
    
    # Set RLS context
    await db.execute("SELECT set_config('app.current_tenant', $1, true)", str(tenant_id))

    query = """
        INSERT INTO app.strs (
            tenant_id, case_id, status, triggering_factors, 
            subject_background, digital_footprints, transaction_summary, created_by
        )
        VALUES ($1, $2, 'draft', $3, $4, $5, $6, $7)
        RETURNING str_id, tenant_id, case_id, status, triggering_factors, 
                  subject_background, digital_footprints, transaction_summary, 
                  created_by, created_at, submitted_by, submitted_at
    """
    try:
        row = await db.fetchrow(
            query, 
            tenant_id, 
            payload.case_id, 
            payload.triggering_factors,
            payload.subject_background, 
            payload.digital_footprints, 
            payload.transaction_summary, 
            user_id
        )
        await auth.log_audit_event(str(user_id), "STR_CREATED", f"Created STR draft with ID {row['str_id']}")
        return dict(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/", response_model=List[STRResponse])
async def list_strs(
    current_user: dict = Depends(auth.get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """
    Retrieve all STRs for the current tenant.
    """
    user_id, tenant_id = await get_user_and_tenant(current_user, db)
    
    # Set RLS context
    await db.execute("SELECT set_config('app.current_tenant', $1, true)", str(tenant_id))

    query = """
        SELECT str_id, tenant_id, case_id, status, triggering_factors, 
               subject_background, digital_footprints, transaction_summary, 
               created_by, created_at, submitted_by, submitted_at
        FROM app.strs
        ORDER BY created_at DESC
    """
    try:
        rows = await db.fetch(query)
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{str_id}", response_model=STRResponse)
async def get_str_detail(
    str_id: UUID,
    current_user: dict = Depends(auth.get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """
    Retrieve a specific STR by its ID.
    """
    user_id, tenant_id = await get_user_and_tenant(current_user, db)
    
    # Set RLS context
    await db.execute("SELECT set_config('app.current_tenant', $1, true)", str(tenant_id))

    query = """
        SELECT str_id, tenant_id, case_id, status, triggering_factors, 
               subject_background, digital_footprints, transaction_summary, 
               created_by, created_at, submitted_by, submitted_at
        FROM app.strs
        WHERE str_id = $1
    """
    row = await db.fetchrow(query, str_id)
    if not row:
        raise HTTPException(status_code=404, detail="STR not found")
        
    return dict(row)

@router.put("/{str_id}", response_model=STRResponse)
async def update_str_draft(
    str_id: UUID,
    payload: STRUpdate,
    current_user: dict = Depends(auth.get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """
    Update fields of a draft STR.
    """
    user_id, tenant_id = await get_user_and_tenant(current_user, db)
    
    # Set RLS context
    await db.execute("SELECT set_config('app.current_tenant', $1, true)", str(tenant_id))

    # Fetch status first to check write constraints
    status_val = await db.fetchval("SELECT status FROM app.strs WHERE str_id = $1", str_id)
    if status_val is None:
        raise HTTPException(status_code=404, detail="STR not found")
        
    if status_val == "filed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Cannot modify a finalized and filed STR."
        )

    query = """
        UPDATE app.strs
        SET case_id = COALESCE($1, case_id),
            triggering_factors = COALESCE($2, triggering_factors),
            subject_background = COALESCE($3, subject_background),
            digital_footprints = COALESCE($4, digital_footprints),
            transaction_summary = COALESCE($5, transaction_summary)
        WHERE str_id = $6
        RETURNING str_id, tenant_id, case_id, status, triggering_factors, 
                  subject_background, digital_footprints, transaction_summary, 
                  created_by, created_at, submitted_by, submitted_at
    """
    try:
        row = await db.fetchrow(
            query, 
            payload.case_id, 
            payload.triggering_factors,
            payload.subject_background, 
            payload.digital_footprints, 
            payload.transaction_summary, 
            str_id
        )
        await auth.log_audit_event(str(user_id), "STR_UPDATED", f"Updated STR draft with ID {str_id}")
        return dict(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/{str_id}/submit", response_model=STRResponse)
async def submit_str(
    str_id: UUID,
    current_user: dict = Depends(auth.get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """
    Finalize and submit the STR to JFIU. Sets status to 'filed'.
    """
    user_id, tenant_id = await get_user_and_tenant(current_user, db)
    
    # Set RLS context
    await db.execute("SELECT set_config('app.current_tenant', $1, true)", str(tenant_id))

    # Fetch status first
    status_val = await db.fetchval("SELECT status FROM app.strs WHERE str_id = $1", str_id)
    if status_val is None:
        raise HTTPException(status_code=404, detail="STR not found")
        
    if status_val == "filed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="STR is already finalized and filed."
        )

    query = """
        UPDATE app.strs
        SET status = 'filed',
            submitted_by = $1,
            submitted_at = now()
        WHERE str_id = $2
        RETURNING str_id, tenant_id, case_id, status, triggering_factors, 
                  subject_background, digital_footprints, transaction_summary, 
                  created_by, created_at, submitted_by, submitted_at
    """
    try:
        row = await db.fetchrow(query, user_id, str_id)
        await auth.log_audit_event(str(user_id), "STR_FILED", f"Finalized and filed STR with ID {str_id}")
        return dict(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
