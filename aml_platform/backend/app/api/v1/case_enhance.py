"""Case-management enhancements (TASK-015 / TASK-017).

Notes, timeline, bulk actions and workflow tracking over app.case_notes and
app.workflow_event (init_scripts/06_case_enhancements.sql). All SQL is
static text with asyncpg $n bind parameters.
"""

from fastapi import APIRouter, Depends

from app.core import auth
from app.core.exceptions import ValidationAppError, database_error
from app.db.session import get_db
from app.services import audit_service

router = APIRouter()


@router.post("/{case_id}/notes", status_code=201)
async def add_case_note(
    case_id: str,
    payload: dict,
    current_user: dict = Depends(auth.get_current_user),
    db=Depends(get_db),
):
    """Add a note to a case. Attachment content upload is deferred to the
    object-store layer (file writes are literal-path confined); metadata
    may be supplied now."""
    body = (payload.get("body") or "").strip()
    if len(body) < 3:
        raise ValidationAppError("note body is required (min 3 chars)")

    user_row = await db.fetchrow(
        "SELECT user_id FROM app.app_users WHERE username = $1", current_user["username"])
    user_id = user_row["user_id"] if user_row else None

    try:
        row = await db.fetchrow(
            "INSERT INTO app.case_notes (case_id, author_id, body, attachment_name, attachment_ref) "
            "VALUES ($1, $2, $3, $4, $5) RETURNING note_id, created_at",
            case_id, user_id, body,
            payload.get("attachment_name"), payload.get("attachment_ref"),
        )
    except Exception as exc:
        raise database_error("cases.add_note", exc)
    await audit_service.record_audit_event(
        "CASE_NOTE_ADDED", actor=current_user, resource_type="CASE",
        resource_id=case_id, db=db,
    )
    return {"status": "success", "note_id": str(row["note_id"])}


@router.get("/{case_id}/notes")
async def list_case_notes(
    case_id: str,
    current_user: dict = Depends(auth.get_current_user),
    db=Depends(get_db),
):
    try:
        rows = await db.fetch(
            "SELECT note_id, author_id, body, attachment_name, created_at "
            "FROM app.case_notes WHERE case_id = $1 ORDER BY created_at DESC",
            case_id,
        )
    except Exception as exc:
        raise database_error("cases.list_notes", exc)
    notes = []
    for row in rows:
        item = dict(row)
        item["note_id"] = str(item["note_id"])
        item["created_at"] = item["created_at"].isoformat()
        notes.append(item)
    return notes


@router.get("/{case_id}/timeline")
async def case_timeline(
    case_id: str,
    current_user: dict = Depends(auth.get_current_user),
    db=Depends(get_db),
):
    """Visual timeline of case activity (TASK-015): workflow events plus
    audit actions for the case, newest first."""
    try:
        wf_rows = await db.fetch(
            "SELECT event_type AS kind, occurred_at AS at, detail::text AS detail "
            "FROM app.workflow_event WHERE case_id = $1",
            case_id,
        )
        audit_rows = await db.fetch(
            "SELECT action AS kind, created_at AS at, reason AS detail "
            "FROM app.audit_access_events WHERE resource_id::text = $1 "
            "ORDER BY created_at DESC LIMIT 100",
            case_id,
        )
    except Exception as exc:
        raise database_error("cases.timeline", exc)
    events = []
    for row in list(wf_rows) + list(audit_rows):
        at = row["at"]
        events.append({
            "kind": row["kind"],
            "at": at.isoformat() if hasattr(at, "isoformat") else at,
            "detail": row["detail"],
        })
    events.sort(key=lambda e: e["at"], reverse=True)
    return events


@router.post("/bulk")
async def bulk_case_action(
    payload: dict,
    current_user: dict = Depends(auth.require_role("DEPARTMENT_HEAD", "ADMIN")),
    db=Depends(get_db),
):
    """Bulk status update over a list of case ids (TASK-015)."""
    case_ids = payload.get("case_ids") or []
    new_status = payload.get("status")
    allowed = {"open", "under_review", "closed"}
    if not case_ids or new_status not in allowed:
        raise ValidationAppError("case_ids (non-empty) and status (open|under_review|closed) required")
    if len(case_ids) > 200:
        raise ValidationAppError("max 200 cases per bulk action")

    updated = 0
    try:
        for case_id in case_ids:
            result = await db.execute(
                "UPDATE app.cases SET status = $1 WHERE case_id = $2", new_status, case_id)
            updated += result
    except Exception as exc:
        raise database_error("cases.bulk", exc)
    await audit_service.record_audit_event(
        "CASE_BULK_UPDATE", actor=current_user, resource_type="CASE",
        reason=f"status={new_status} count={len(case_ids)}", db=db,
    )
    return {"status": "success", "updated": updated, "target": len(case_ids)}


@router.get("/workflow/stale")
async def stale_workflows(
    current_user: dict = Depends(auth.require_role("ADMIN")),
    db=Depends(get_db),
):
    """TASK-017: surface workflow instances stuck mid-flight (started but
    never completed/failed) so operators can intervene."""
    try:
        rows = await db.fetch(
            "SELECT case_id, case_number, workflow_instance_id, status, workflow_status, created_at "
            "FROM app.cases "
            "WHERE workflow_instance_id IS NOT NULL "
            "  AND (workflow_status IS NULL OR workflow_status = 'running') "
            "  AND status NOT IN ('closed', 'approved') "
            "ORDER BY created_at DESC LIMIT 100"
        )
    except Exception as exc:
        raise database_error("cases.stale_workflows", exc)
    return [dict(r, case_id=str(r["case_id"])) for r in rows]


async def record_workflow_event(db, case_id: str, instance_id: str, task_key: str,
                                event_type: str, detail: dict) -> None:
    """Record a workflow transition (called by the main cases router)."""
    import json as _json

    detail_text = _json.dumps(detail)  # value only — no SQL text is built
    await db.execute(
        "INSERT INTO app.workflow_event (case_id, workflow_instance_id, task_key, event_type, detail) "
        "VALUES ($1, $2, $3, $4, $5::jsonb)",
        case_id, instance_id, task_key, event_type, detail_text,
    )
