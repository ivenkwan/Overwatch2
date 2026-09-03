# aml_platform/backend/app/api/v1/strs.py

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from app.core.exceptions import NotFoundError, ValidationAppError, ConflictError, database_error
from typing import List
from uuid import UUID
import asyncpg
from app.db.session import get_db
from app.core import auth
from app.schemas.str_schema import STRCreate, STRUpdate, STRResponse
from app.services import str_service

router = APIRouter()

STR_COLUMNS = """str_id, tenant_id, case_id, status, triggering_factors,
               subject_background, digital_footprints, transaction_summary,
               created_by, created_at, submitted_by, submitted_at"""

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
        raise database_error("strs.write", e)

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
        raise database_error("strs.write", e)

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
        raise NotFoundError("STR not found")
        
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

    # Set RLS context (and the acting user for the version-history trigger)
    await db.execute("SELECT set_config('app.current_tenant', $1, true)", str(tenant_id))
    await db.execute("SELECT set_config('app.actor_user_id', $1, true)", str(user_id))

    # Fetch status first to check write constraints
    status_val = await db.fetchval("SELECT status FROM app.strs WHERE str_id = $1", str_id)
    if status_val is None:
        raise NotFoundError("STR not found")

    if status_val == "filed":
        raise ConflictError("Cannot modify a finalized and filed STR.")

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
        raise database_error("strs.write", e)

@router.post("/{str_id}/review", response_model=STRResponse)
async def review_str(
    str_id: UUID,
    current_user: dict = Depends(auth.get_current_user_with_scope("SENIOR_INVESTIGATOR")),
    db: asyncpg.Connection = Depends(get_db)
):
    """Move a draft STR into review (draft -> under_review)."""
    return await _transition_str(str_id, "under_review", current_user, db)


@router.post("/{str_id}/withdraw", response_model=STRResponse)
async def withdraw_str(
    str_id: UUID,
    current_user: dict = Depends(auth.get_current_user_with_scope("SENIOR_INVESTIGATOR")),
    db: asyncpg.Connection = Depends(get_db)
):
    """Withdraw an STR that is not yet filed."""
    return await _transition_str(str_id, "withdrawn", current_user, db)


async def _transition_str(str_id: UUID, target: str, current_user: dict, db) -> dict:
    user_id, tenant_id = await get_user_and_tenant(current_user, db)
    await db.execute("SELECT set_config('app.current_tenant', $1, true)", str(tenant_id))
    await db.execute("SELECT set_config('app.actor_user_id', $1, true)", str(user_id))

    current = await db.fetchval("SELECT status FROM app.strs WHERE str_id = $1", str_id)
    if current is None:
        raise NotFoundError("STR not found")
    if not str_service.can_transition(current, target):
        raise ConflictError(f"Cannot move STR from '{current}' to '{target}'")

    query = f"""
        UPDATE app.strs SET status = $1
        WHERE str_id = $2
        RETURNING {STR_COLUMNS}
    """
    try:
        row = await db.fetchrow(query, target, str_id)
        await auth.log_audit_event(
            str(user_id), "STR_STATUS_CHANGED",
            f"STR {str_id}: {current} -> {target}", tenant_id=str(tenant_id), db=db,
        )
        return dict(row)
    except Exception as e:
        raise database_error("strs.transition", e)


@router.get("/{str_id}/versions")
async def list_str_versions(
    str_id: UUID,
    current_user: dict = Depends(auth.get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """Version history index for an STR (append-only audit of every change)."""
    user_id, tenant_id = await get_user_and_tenant(current_user, db)
    await db.execute("SELECT set_config('app.current_tenant', $1, true)", str(tenant_id))
    try:
        rows = await db.fetch(
            """
            SELECT version_no, changed_by, changed_at
            FROM app.str_versions
            WHERE str_id = $1
            ORDER BY version_no DESC
            """,
            str_id,
        )
        return {"str_id": str(str_id), "versions": [
            {"version_no": r["version_no"],
             "changed_by": str(r["changed_by"]) if r["changed_by"] else None,
             "changed_at": r["changed_at"].isoformat()} for r in rows
        ]}
    except Exception as e:
        raise database_error("strs.versions", e)


@router.get("/{str_id}/versions/{version_no}")
async def get_str_version(
    str_id: UUID,
    version_no: int,
    current_user: dict = Depends(auth.get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """Fetch one snapshot from the STR version history."""
    user_id, tenant_id = await get_user_and_tenant(current_user, db)
    await db.execute("SELECT set_config('app.current_tenant', $1, true)", str(tenant_id))
    row = await db.fetchrow(
        "SELECT version_no, snapshot, changed_by, changed_at FROM app.str_versions "
        "WHERE str_id = $1 AND version_no = $2",
        str_id, version_no,
    )
    if not row:
        raise NotFoundError(f"Version {version_no} not found for STR {str_id}")
    return {"str_id": str(str_id), "version_no": row["version_no"],
            "snapshot": row["snapshot"], "changed_at": row["changed_at"].isoformat()}


@router.get("/{str_id}/export.pdf")
async def export_str_pdf(
    str_id: UUID,
    current_user: dict = Depends(auth.get_current_user_with_scope("SENIOR_INVESTIGATOR")),
    db: asyncpg.Connection = Depends(get_db)
):
    """Export the STR as a PDF. The content SHA-256 (integrity anchor for
    digital signing) is returned in the X-Content-Sha256 header."""
    user_id, tenant_id = await get_user_and_tenant(current_user, db)
    await db.execute("SELECT set_config('app.current_tenant', $1, true)", str(tenant_id))
    row = await db.fetchrow(f"SELECT {STR_COLUMNS} FROM app.strs WHERE str_id = $1", str_id)
    if not row:
        raise NotFoundError("STR not found")

    record = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dict(row).items()}
    pdf_bytes = str_service.build_str_pdf(record)
    await auth.log_audit_event(
        str(user_id), "STR_EXPORTED", f"Exported STR {str_id} as PDF",
        tenant_id=str(tenant_id), db=db,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"X-Content-Sha256": str_service.content_sha256(record),
                 "Content-Disposition": f'attachment; filename="str_{str_id}.pdf"'},
    )


@router.post("/{str_id}/submit", response_model=STRResponse)
async def submit_str(
    str_id: UUID,
    current_user: dict = Depends(auth.get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """
    Finalize and submit the STR to JFIU. Mandatory fields are validated and
    the filing transition is enforced (draft/under_review -> filed).
    """
    user_id, tenant_id = await get_user_and_tenant(current_user, db)

    # Set RLS context
    await db.execute("SELECT set_config('app.current_tenant', $1, true)", str(tenant_id))
    await db.execute("SELECT set_config('app.actor_user_id', $1, true)", str(user_id))

    row = await db.fetchrow(f"SELECT {STR_COLUMNS} FROM app.strs WHERE str_id = $1", str_id)
    if row is None:
        raise NotFoundError("STR not found")

    record = dict(row)
    if not str_service.can_transition(record["status"], "filed"):
        raise ConflictError(f"STR cannot be filed from status '{record['status']}'.")

    problems = str_service.validate_str_submission(record)
    if problems:
        raise ValidationAppError(
            "STR is missing mandatory content required for JFIU filing",
            details={"fields": problems},
        )

    query = f"""
        UPDATE app.strs
        SET status = 'filed',
            submitted_by = $1,
            submitted_at = now()
        WHERE str_id = $2
        RETURNING {STR_COLUMNS}
    """
    try:
        filed = await db.fetchrow(query, user_id, str_id)
        await auth.log_audit_event(
            str(user_id), "STR_FILED",
            f"Finalized and filed STR {str_id} (sha256={str_service.content_sha256(record)})",
            tenant_id=str(tenant_id), db=db,
        )
        return dict(filed)
    except Exception as e:
        raise database_error("strs.write", e)
