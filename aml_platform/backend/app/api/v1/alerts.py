from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from app.core.exceptions import NotFoundError, database_error
from typing import List
from app.services import pii_service, audit_service
from app.core import auth
from app.db.session import get_db
import asyncpg

router = APIRouter()


def _jsonable(rows: list) -> list:
    """Convert DB rows (datetimes/decimals) into JSON-serializable dicts."""
    from decimal import Decimal

    out = []
    for row in rows:
        item = {}
        for key, value in dict(row).items():
            if hasattr(value, "isoformat"):
                item[key] = value.isoformat()
            elif isinstance(value, Decimal):
                item[key] = float(value)
            else:
                item[key] = value
        out.append(item)
    return out

@router.get("/feed")
async def get_monitoring_feed(
    current_user: dict = Depends(auth.get_current_user),
    limit: int = Query(150, ge=1, le=500),
    min_hkd: float | None = Query(None, ge=0),
    txn_type: str | None = Query(None, max_length=32),
    db: asyncpg.Connection = Depends(get_db)
):
    """Monitoring feed with server-side filters (TASK-012): optional
    minimum amount and transaction-type filters execute in SQL, never in
    the client. Responses carry short-lived Cache-Control headers."""
    query = """
        SELECT txn_hash, customer_num, counterparty_id, txn_date, txn_ref_no,
               txn_country, txn_currency, txn_currency_amount, txn_amount_in_hkd,
               cdi_code, txn_type
        FROM core.transactions
        WHERE ($1::float8 IS NULL OR txn_amount_in_hkd >= $1)
          AND ($2::text IS NULL OR txn_type = $2)
        ORDER BY txn_date DESC
        LIMIT $3
    """
    rows = await db.fetch(query, min_hkd, txn_type, limit)
    feed = _jsonable(rows)
    response = JSONResponse(pii_service.mask_pii(feed, current_user["role"]))
    response.headers["Cache-Control"] = "private, max-age=5"
    return response

@router.get("/")
async def get_alerts(
    current_user: dict = Depends(auth.get_current_user),
    status: str = 'OPEN',
    limit: int = Query(100, ge=1, le=500),
    min_hkd: float | None = Query(None, ge=0),
    txn_type: str | None = Query(None, max_length=32),
    db: asyncpg.Connection = Depends(get_db)
):
    """Alert list (currently over core.transactions until the alert table
    exists) with server-side filters (TASK-012)."""
    query = """
        SELECT * FROM core.transactions
        WHERE ($1::float8 IS NULL OR txn_amount_in_hkd >= $1)
          AND ($2::text IS NULL OR txn_type = $2)
        ORDER BY txn_date DESC
        LIMIT $3
    """
    rows = await db.fetch(query, min_hkd, txn_type, limit)
    alerts = _jsonable(rows)
    response = JSONResponse(pii_service.mask_pii(alerts, current_user["role"]))
    response.headers["Cache-Control"] = "private, max-age=5"
    return response

@router.get("/{alert_id}")
async def get_alert_detail(
    alert_id: str,
    current_user: dict = Depends(auth.get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    query = "SELECT * FROM core.transactions WHERE txn_hash = $1"
    row = await db.fetchrow(query, alert_id)
    if not row:
        raise NotFoundError("Alert not found")
    
    alert = dict(row)
    
    if current_user["role"] in ["SENIOR_INVESTIGATOR", "DEPARTMENT_HEAD"]:
        await audit_service.log_unmasking_event(current_user, "ALERT", str(alert_id), db=db)
        
    return pii_service.mask_pii(alert, current_user["role"])

@router.post("/{alert_id}/assign")
async def assign_alert(alert_id: str, current_user: dict = Depends(auth.get_current_user), db: asyncpg.Connection = Depends(get_db)):
    # Note: Using upsert pattern for demo purposes if alert doesn't formally exist in app.alerts yet
    query = """
        INSERT INTO app.alerts (tenant_id, alert_type, status, created_by)
        VALUES ($1, 'TRANSACTION_MONITORING', 'triaged', $2)
        ON CONFLICT (alert_id) DO UPDATE SET status = 'triaged'
        RETURNING alert_id, status
    """
    # Assuming user's tenant_id is retrieved from their current_user object, here we use a dummy or skip it for simplicity
    # For now, let's just update if it exists, or loosely mock the DB transition without breaking constraints
    update_query = "UPDATE app.alerts SET status = 'triaged' WHERE payload->>'txn_hash' = $1 RETURNING alert_id"
    res = await db.fetchrow(update_query, alert_id)
    await audit_service.record_audit_event(
        "ALERT_ASSIGNED", actor=current_user, resource_type="ALERT", resource_id=alert_id, db=db
    )
    return {"status": "assigned", "alert_id": alert_id}

@router.post("/{alert_id}/propose-close")
async def propose_close(alert_id: str, notes: str, current_user: dict = Depends(auth.get_current_user), db: asyncpg.Connection = Depends(get_db)):
    update_query = "UPDATE app.alerts SET status = 'escalated' WHERE payload->>'txn_hash' = $1 RETURNING alert_id"
    await db.fetchrow(update_query, alert_id)
    await audit_service.record_audit_event(
        "ALERT_CLOSE_PROPOSED", actor=current_user, resource_type="ALERT",
        resource_id=alert_id, reason=notes, db=db,
    )
    return {"status": "proposed_close", "notes": notes, "alert_id": alert_id}

@router.post("/{alert_id}/approve")
async def approve_close(alert_id: str, current_user: dict = Depends(auth.get_current_user_with_scope("SENIOR_INVESTIGATOR")), db: asyncpg.Connection = Depends(get_db)):
    update_query = "UPDATE app.alerts SET status = 'closed' WHERE payload->>'txn_hash' = $1 RETURNING alert_id"
    await db.fetchrow(update_query, alert_id)
    await audit_service.record_audit_event(
        "ALERT_CLOSE_APPROVED", actor=current_user, resource_type="ALERT", resource_id=alert_id, db=db
    )
    return {"status": "approved", "alert_id": alert_id}

@router.post("/{alert_id}/reject")
async def reject_close(alert_id: str, notes: str, current_user: dict = Depends(auth.get_current_user_with_scope("SENIOR_INVESTIGATOR")), db: asyncpg.Connection = Depends(get_db)):
    if not notes or len(notes.strip()) < 5:
        raise HTTPException(status_code=400, detail="Mandatory notes required for rejection.")
    
    update_query = "UPDATE app.alerts SET status = 'open' WHERE payload->>'txn_hash' = $1 RETURNING alert_id"
    await db.fetchrow(update_query, alert_id)
    await audit_service.record_audit_event(
        "ALERT_CLOSE_REJECTED", actor=current_user, resource_type="ALERT",
        resource_id=alert_id, reason=notes, db=db,
    )
    return {"status": "rejected", "notes": notes, "alert_id": alert_id}
