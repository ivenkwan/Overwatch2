"""
Public audit API (TASK-004).

Wraps app.services.audit_store with the logger mirror, actor resolution and
input normalisation. Design rules:

  * record_audit_event() NEVER raises — an audit failure must not break the
    audited request; every event is mirrored to the `aml_audit` logger so a
    log-file trail survives database outages.
  * All values are normalised to typed parameters before reaching SQL; string
    identifiers that are not UUIDs travel inside the `reason` text.
"""

import logging
from typing import Optional

from app.services import audit_store
from app.services.audit_store import to_uuid

audit_logger = logging.getLogger("aml_audit")

MAX_REASON_LENGTH = 2000


def _build_reason(username: Optional[str], reason: Optional[str], resource_id: Optional[str]) -> Optional[str]:
    parts = []
    if username:
        parts.append(f"actor={username}")
    if reason:
        parts.append(reason)
    if resource_id is not None and to_uuid(resource_id) is None:
        # Non-UUID identifiers (txn hashes, entity ids) live in the reason
        # trail — the resource_id column only accepts UUIDs.
        parts.append(f"resource={resource_id}")
    text = " ".join(parts)[:MAX_REASON_LENGTH]
    return text or None


async def record_audit_event(
    action: str,
    *,
    actor: Optional[dict] = None,
    actor_id: Optional[str] = None,
    resource_type: str = "PLATFORM",
    resource_id: Optional[str] = None,
    decision: str = "allow",
    reason: Optional[str] = None,
    tenant_id: Optional[str] = None,
    db=None,
) -> bool:
    """Persist one audit event to the hash-chained table. True on DB success."""
    if decision not in ("allow", "deny"):
        decision = "allow"

    if actor_id is None:
        actor_id = (actor or {}).get("id")
    username = (actor or {}).get("username")

    details = _build_reason(username, reason, resource_id)
    audit_logger.info(
        "AUDIT | USER:%s | ACTION:%s | RES:%s | DECISION:%s | DATA:%s",
        actor_id, action, resource_type, decision, details,
    )

    try:
        user_uuid = None
        if actor_id is not None:
            user_uuid = to_uuid(actor_id) or await audit_store.resolve_local_user_id(db, actor_id)

        await audit_store.insert_audit_event(
            db,
            to_uuid(tenant_id),
            user_uuid,
            resource_type,
            to_uuid(resource_id),
            action,
            decision,
            details,
        )
        return True
    except Exception as exc:
        audit_logger.error("Audit DB write failed (logger fallback above): %s", exc)
        return False


async def log_unmasking_event(user: dict, resource_type: str, resource_id: str, db=None) -> bool:
    """Compliance-critical: log whenever a Senior Investigator views raw PII."""
    return await record_audit_event(
        "PII_UNMASKED",
        actor=user,
        resource_type=resource_type,
        resource_id=resource_id,
        reason=f"Viewed raw PII for {resource_type}",
        db=db,
    )


def export_audit_events_ndjson(events: list) -> str:
    """Render audit events as newline-delimited JSON for SIEM ingestion."""
    import json

    lines = []
    for e in events:
        created_at = e.get("created_at")
        record = {
            "event_id": str(e.get("event_id")),
            "timestamp": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
            "tenant_id": str(e.get("tenant_id")) if e.get("tenant_id") else None,
            "user_id": str(e.get("user_id")) if e.get("user_id") else None,
            "resource_type": e.get("resource_type"),
            "resource_id": str(e.get("resource_id")) if e.get("resource_id") else None,
            "action": e.get("action"),
            "decision": e.get("decision"),
            "reason": e.get("reason"),
            "previous_hash": e.get("previous_hash"),
            "record_hash": e.get("record_hash"),
        }
        lines.append(json.dumps(record, ensure_ascii=False, default=str))
    return "\n".join(lines)
