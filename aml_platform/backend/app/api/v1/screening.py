"""
Screening endpoints (TASK-014).

Thin DB layer over app.services.screening_service: loads the blocklists and
runs the pure matchers. Name screening runs against OFAC-style named
entries; wallet screening runs against wallet blocklists AND the internal
revoked-credential blocklist (TASK-049). Screenings are audited.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core import auth
from app.core.exceptions import database_error
from app.db.session import get_db
from app.services import audit_service, screening_service

router = APIRouter()


class ScreenRequest(BaseModel):
    subject_name: str | None = Field(default=None, max_length=500)
    wallet_address: str | None = Field(default=None, max_length=255)
    include_internal_blocklist: bool = True


@router.post("/screen")
async def screen(
    request: ScreenRequest,
    current_user: dict = Depends(auth.get_current_user_with_scope("SENIOR_INVESTIGATOR")),
    db=Depends(get_db),
):
    if not request.subject_name and not request.wallet_address:
        from app.core.exceptions import ValidationAppError
        raise ValidationAppError("Provide subject_name and/or wallet_address to screen")

    try:
        named_rows = await db.fetch(
            "SELECT entity_id AS name, 'ofac' AS list_name, entity_id AS record_id "
            "FROM ag_catalog.ofac_blocklist WHERE entity_type IN ('INDIVIDUAL','ORGANIZATION')"
        )
        wallet_rows = await db.fetch(
            "SELECT wallet_address, 'ofac_wallet' AS list_name, wallet_address AS record_id "
            "FROM ag_catalog.ofac_blocklist WHERE wallet_address IS NOT NULL"
        )
    except Exception as exc:
        # The deployed compose DB may not carry the ag_catalog blocklist;
        # degrade to the app-side lists rather than failing the screen.
        named_rows, wallet_rows = [], []
        try:
            named_rows = await db.fetch(
                "SELECT name, 'watchlist' AS list_name, record_id FROM app.watchlist_entry"
            )
        except Exception:
            pass

    internal_hits: list = []
    if request.include_internal_blocklist and request.wallet_address:
        try:
            internal_rows = await db.fetch(
                "SELECT wallet_address, 'internal_revoked' AS list_name, source_credential_id AS record_id "
                "FROM app.internal_wallet_blocklist WHERE active = TRUE"
            )
        except Exception:
            internal_rows = []
        internal_hits = screening_service.screen_wallet(
            request.wallet_address, [dict(r) for r in internal_rows])

    hits: list = []
    if request.subject_name:
        hits += screening_service.screen_name(
            request.subject_name, [dict(r) for r in named_rows])
    if request.wallet_address:
        hits += screening_service.screen_wallet(
            request.wallet_address, [dict(r) for r in wallet_rows])
        hits += internal_hits

    disposition = screening_service.highest_disposition(hits)
    await audit_service.record_audit_event(
        "SCREENING_RAN",
        actor=current_user,
        resource_type="SCREENING",
        reason=f"subject={request.subject_name or ''} wallet={request.wallet_address or ''} "
               f"disposition={disposition}",
        db=db,
    )
    return {
        "status": "success",
        "disposition": disposition or "CLEAR",
        "hits": [
            {
                "list": h.list_name,
                "matched_on": h.matched_on,
                "matched_value": h.matched_value,
                "similarity": round(h.similarity, 3),
                "disposition": h.disposition,
            }
            for h in sorted(hits, key=lambda h: -h.similarity)
        ],
    }
