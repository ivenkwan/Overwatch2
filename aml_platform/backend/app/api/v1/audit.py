"""
Audit trail endpoints (TASK-004): SIEM export and tamper-evidence verification.

Both endpoints are restricted to ADMIN users.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.core import auth
from app.db.session import get_db
from app.services import audit_service, audit_store
import asyncpg

router = APIRouter()


@router.get("/export", response_class=PlainTextResponse)
async def export_audit_events(
    since: Optional[datetime] = Query(None, description="ISO timestamp lower bound"),
    until: Optional[datetime] = Query(None, description="ISO timestamp upper bound"),
    limit: int = Query(1000, ge=1, le=10000),
    current_user: dict = Depends(auth.require_role("ADMIN")),
    db: asyncpg.Connection = Depends(get_db),
):
    """Export audit events as NDJSON for SIEM ingestion (one JSON object per line)."""
    try:
        events = await audit_store.fetch_audit_events(db, since=since, until=until, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Audit export failed")
    await audit_service.record_audit_event(
        "AUDIT_EXPORTED",
        actor=current_user,
        resource_type="AUDIT_TRAIL",
        reason=f"Exported {len(events)} audit events",
        db=db,
    )
    return audit_service.export_audit_events_ndjson(events)


@router.get("/verify")
async def verify_audit_chain(
    current_user: dict = Depends(auth.require_role("ADMIN")),
    db: asyncpg.Connection = Depends(get_db),
):
    """Recompute the audit hash chain and report whether it is intact."""
    try:
        return await audit_store.verify_audit_chain(db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Chain verification failed")
