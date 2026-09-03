"""
Pure planning logic for the T1_CREDENTIAL_STATUS batch (AWI TASK-048).

Kept free of Dagster/DB imports so it is unit-testable from the backend
test suite (backend/tests/test_awi_phase1.py).
"""

from datetime import datetime, timezone


def plan_status_updates(records, verdicts, now=None):
    """Map verification verdicts onto DB updates.

    records:  [{credential_id, expires_at, wallet_instruments: [..]}]
    verdicts: [{valid, vct, expiresAt, reason?, error?}] aligned by index.
    Returns dict with credential_updates [(status, credential_id)],
    deauthorizations [instrument_id], dlq [(credential_id, reason)].
    """
    now = now or datetime.now(timezone.utc)
    credential_updates, deauthorizations, dlq = [], [], []

    by_index = list(verdicts or [])
    for i, rec in enumerate(records):
        verdict = by_index[i] if i < len(by_index) else None
        if verdict is None:
            dlq.append((rec["credential_id"], "no verdict returned by provider"))
            continue

        if verdict.get("error"):
            dlq.append((rec["credential_id"], str(verdict["error"])[:500]))
            continue

        if verdict.get("valid") is False:
            reason = (verdict.get("reason") or "").lower()
            status = "REVOKED" if "revok" in reason or "status" in reason else "EXPIRED"
            credential_updates.append((status, rec["credential_id"]))
            deauthorizations.extend(rec.get("wallet_instruments") or [])
            continue

        expires_at = verdict.get("expiresAt") or rec.get("expires_at")
        if expires_at:
            try:
                exp = expires_at if isinstance(expires_at, datetime) else datetime.fromisoformat(
                    str(expires_at).replace("Z", "+00:00"))
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp <= now:
                    credential_updates.append(("EXPIRED", rec["credential_id"]))
                    deauthorizations.extend(rec.get("wallet_instruments") or [])
                    continue
                if (exp - now).days <= 90:
                    credential_updates.append(("REFRESH_DUE", rec["credential_id"]))
                    continue
            except ValueError:
                dlq.append((rec["credential_id"], f"unparseable expiresAt: {expires_at}"))
                continue

    return {"credential_updates": credential_updates,
            "deauthorizations": deauthorizations,
            "dlq": dlq}
