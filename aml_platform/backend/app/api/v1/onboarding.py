"""
Authorized-wallet onboarding API (AWI TASK-038 / TASK-040 / TASK-042).

Flow (ADR-0002, Option C):
  1. POST /verify            — submit a KYC/KYB credential; verified via
                                didvc-edge M2M; party + party_credential rows
                                are upserted idempotently (the long-missing
                                producer for the party/UBO dimension).
  2. POST /wallets           — maker registers a wallet authorization
                                (address-control proof performed by
                                wallet_proof); row lands UNAUTHORIZED.
  3. POST /wallets/{id}/approve — checker (a DIFFERENT user) activates the
                                authorization (maker-checker, TASK-040).
  4. POST /wallets/{id}/revoke — either maker or checker deactivates.

Authorization is a risk signal only — it never exempts screening (ADR-0002).
All writes are audited; tenant context is established fail-closed.
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

import asyncpg
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core import auth
from app.core.exceptions import (
    AuthorizationAppError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
    ServiceUnavailableError,
    database_error,
)
from app.core.tenancy import get_tenant_db
from app.db.session import get_db
from app.services import audit_service, identity_provider, wallet_proof

router = APIRouter()

AUTHZ_MAX_DAYS = int(os.getenv("AUTHZ_MAX_DAYS", "365") or "365")


class CredentialSubmission(BaseModel):
    credential: str = Field(min_length=20)
    include_claims: bool = False


class WalletRegistration(BaseModel):
    party_id: str = Field(min_length=1, max_length=255)
    blockchain: str = Field(pattern="^(ETHEREUM|POLYGON|SOLANA|TRON|OTHER)$")
    wallet_address: str = Field(min_length=8, max_length=255)
    custody_type: Optional[str] = None
    instrument_id: Optional[str] = None
    # address-control proof: either a fresh challenge+signature (verified here)
    # or a previously recorded proof reference (issuer-attested path)
    challenge: Optional[str] = None
    signature: Optional[str] = None
    proof_ref: Optional[str] = None


@router.get("/challenge")
async def issue_wallet_challenge(
    wallet_address: str = Query(min_length=8, max_length=255),
    blockchain: str = Query(default="ETHEREUM"),
    current_user: dict = Depends(auth.require_role("ADMIN")),
):
    """Issue a single-use, TTL-bounded challenge for address-control proofs."""
    challenge = wallet_proof.issue_challenge(wallet_address, blockchain)
    await audit_service.record_audit_event(
        "WALLET_CHALLENGE_ISSUED", actor=current_user,
        resource_type="WALLET", resource_id=wallet_address, db=None,
    )
    return challenge


@router.post("/verify")
async def verify_credential(
    submission: CredentialSubmission,
    current_user: dict = Depends(auth.require_role("ADMIN")),
    db: asyncpg.Connection = Depends(get_db),
):
    """Verify a KYC/KYB credential and record it against a party (idempotent)."""
    db, ctx = await get_tenant_db(current_user, db)

    verdict = await identity_provider.verify_credential(
        submission.credential, include_claims=submission.include_claims
    )

    await audit_service.record_audit_event(
        "ONBOARDING_VERIFIED" if verdict.get("valid") else "ONBOARDING_REJECTED",
        actor=current_user,
        resource_type="CREDENTIAL",
        reason=f"vct={verdict.get('vct')} evidence={verdict.get('evidence_hash')}",
        tenant_id=str(ctx.tenant_id),
        db=db,
    )

    if not verdict.get("valid"):
        return {"status": "rejected", "verdict": _public_verdict(verdict)}

    claims = verdict.get("claims") or {}
    vct = verdict.get("vct") or "unknown"
    party_type = "LEGAL" if vct in ("hkt_licensed_institution_v1", "hkt_corporate_v1") else "NATURAL"

    credential_id = "cred_" + (verdict.get("evidence_hash") or "")[:32]
    display_name = claims.get("givenName") or claims.get("registrationNoHash") or f"party:{vct}"
    jurisdiction = claims.get("jurisdiction") or claims.get("nationality")

    try:
        async with db.transaction():
            party_id = "P_" + credential_id[5:21]
            await db.fetchrow(
                """
                INSERT INTO app.party (party_id, party_type, display_name, kyc_status,
                                   jurisdiction, did, onboarding_channel)
                VALUES ($1, $2, $3, 'VERIFIED', $4, $5, 'VC_ISSUER')
                ON CONFLICT (party_id) DO UPDATE
                    SET kyc_status = 'VERIFIED',
                        jurisdiction = COALESCE(EXCLUDED.jurisdiction, app.party.jurisdiction)
                RETURNING party_id
                """,
                party_id, party_type, display_name, jurisdiction, claims.get("sub"),
            )
            await db.fetchrow(
                """
                INSERT INTO app.party_credential
                    (credential_id, party_id, vct, issuer_did, verified_at,
                     expires_at, status, evidence_hash, last_checked_at, claims)
                VALUES ($1, $2, $3, $4, now(),
                        $5::timestamptz, 'ACTIVE', $6, now(), $7::jsonb)
                ON CONFLICT (party_id, vct, issuer_did) DO UPDATE
                    SET verified_at = now(),
                        expires_at = EXCLUDED.expires_at,
                        status = 'ACTIVE',
                        evidence_hash = EXCLUDED.evidence_hash,
                        last_checked_at = now(),
                        claims = EXCLUDED.claims
                RETURNING credential_id
                """,
                credential_id, party_id, vct, verdict.get("issuerDid") or "unknown",
                _iso(verdict.get("expiresAt")), verdict.get("evidence_hash"),
                _json(claims),
            )
    except Exception as e:
        raise database_error("onboarding.verify", e)

    return {
        "status": "verified",
        "party_id": party_id,
        "credential_id": credential_id,
        "verdict": _public_verdict(verdict),
    }


@router.post("/wallets", status_code=201)
async def register_wallet(
    registration: WalletRegistration,
    current_user: dict = Depends(auth.require_role("ADMIN")),
    db: asyncpg.Connection = Depends(get_db),
):
    """Maker step: register a wallet authorization (lands UNAUTHORIZED)."""
    db, ctx = await get_tenant_db(current_user, db)

    if registration.challenge and registration.signature:
        if registration.blockchain in ("ETHEREUM", "POLYGON"):
            proof = wallet_proof.verify_evm_signature(registration.challenge, registration.signature)
        elif registration.blockchain == "SOLANA":
            proof = wallet_proof.verify_solana_signature(
                registration.challenge, registration.signature, registration.wallet_address)
        else:
            raise ValidationAppError("Signature proofs not supported for this chain")
        proof_ref_value = proof["proof_ref"]
        verified_address = proof["address"]
    elif registration.proof_ref:
        proof_ref_value = registration.proof_ref
        verified_address = wallet_proof.normalize_address(
            registration.wallet_address, registration.blockchain)
    else:
        raise ValidationAppError(
            "Address-control proof required: provide challenge+signature or proof_ref"
        )

    instrument_id = registration.instrument_id or (
        f"{registration.blockchain}:{verified_address}".lower()
    )

    try:
        row = await db.fetchrow(
            """
            INSERT INTO app.wallet_authorization
                (instrument_id, blockchain, wallet_address, address_proof, proof_ref,
                 custody_type, party_id, authorized, authorized_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, FALSE, $8)
            ON CONFLICT (blockchain, wallet_address) DO UPDATE
                SET proof_ref = EXCLUDED.proof_ref,
                    custody_type = EXCLUDED.custody_type,
                    party_id = EXCLUDED.party_id,
                    authorized = FALSE,
                    authorized_by = EXCLUDED.authorized_by,
                    approved_by = NULL
            RETURNING instrument_id, authorized, authorized_by
            """,
            instrument_id, registration.blockchain, verified_address,
            "SIGNATURE" if registration.signature else "ISSUER_ATTESTED",
            proof_ref_value, registration.custody_type, registration.party_id,
            str(ctx.user_id),
        )
    except asyncpg.ForeignKeyViolationError:
        raise ValidationAppError("Unknown party_id — verify the credential first")
    except Exception as e:
        raise database_error("onboarding.register_wallet", e)

    await audit_service.record_audit_event(
        "WALLET_AUTHORIZATION_PROPOSED", actor=current_user,
        resource_type="WALLET", resource_id=instrument_id,
        reason=f"party={registration.party_id} proof={proof_ref_value}",
        tenant_id=str(ctx.tenant_id), db=db,
    )
    return {"status": "proposed", "instrument_id": row["instrument_id"],
            "authorized": False, "maker": str(ctx.user_id),
            "note": "awaiting checker approval"}


@router.post("/wallets/{instrument_id}/approve")
async def approve_wallet(
    instrument_id: str,
    current_user: dict = Depends(auth.require_role("ADMIN")),
    db: asyncpg.Connection = Depends(get_db),
):
    """Checker step: activate the authorization. Must be a different user
    from the maker (maker-checker, TASK-040)."""
    db, ctx = await get_tenant_db(current_user, db)

    row = await db.fetchrow(
        "SELECT authorized, authorized_by FROM app.wallet_authorization WHERE instrument_id = $1",
        instrument_id,
    )
    if not row:
        raise NotFoundError(f"Wallet {instrument_id} not registered")
    if row["authorized"]:
        raise ConflictError("Wallet is already authorized")
    if str(row["authorized_by"]) == str(ctx.user_id):
        raise AuthorizationAppError("Maker and checker must be different users")

    valid_until = datetime.utcnow() + timedelta(days=AUTHZ_MAX_DAYS)
    try:
        updated = await db.fetchrow(
            """
            UPDATE app.wallet_authorization
            SET authorized = TRUE, approved_by = $1,
                authorized_from = now(), authorized_until = $2::timestamptz
            WHERE instrument_id = $3
            RETURNING instrument_id, authorized, authorized_until
            """,
            str(ctx.user_id), valid_until.isoformat(), instrument_id,
        )
    except Exception as e:
        raise database_error("onboarding.approve_wallet", e)

    await audit_service.record_audit_event(
        "WALLET_AUTHORIZATION_APPROVED", actor=current_user,
        resource_type="WALLET", resource_id=instrument_id,
        reason=f"until={valid_until.isoformat()}",
        tenant_id=str(ctx.tenant_id), db=db,
    )
    return {"status": "authorized", "instrument_id": updated["instrument_id"],
            "authorized_until": updated["authorized_until"].isoformat()}


@router.post("/wallets/{instrument_id}/revoke")
async def revoke_wallet(
    instrument_id: str,
    current_user: dict = Depends(auth.require_role("ADMIN")),
    db: asyncpg.Connection = Depends(get_db),
):
    """Deactivate an authorization (revocation kills the risk signal)."""
    db, ctx = await get_tenant_db(current_user, db)

    row = await db.fetchrow(
        "SELECT authorized FROM app.wallet_authorization WHERE instrument_id = $1",
        instrument_id,
    )
    if not row:
        raise NotFoundError(f"Wallet {instrument_id} not registered")

    try:
        await db.fetchrow(
            """
            UPDATE app.wallet_authorization
            SET authorized = FALSE, approved_by = NULL, authorized_until = NULL
            WHERE instrument_id = $1
            RETURNING instrument_id
            """,
            instrument_id,
        )
    except Exception as e:
        raise database_error("onboarding.revoke_wallet", e)

    await audit_service.record_audit_event(
        "WALLET_AUTHORIZATION_REVOKED", actor=current_user,
        resource_type="WALLET", resource_id=instrument_id,
        tenant_id=str(ctx.tenant_id), db=db,
    )
    return {"status": "revoked", "instrument_id": instrument_id}


@router.get("/wallets")
async def list_wallets(
    only_authorized: bool = Query(default=False),
    current_user: dict = Depends(auth.get_current_user),
    db: asyncpg.Connection = Depends(get_db),
):
    """List wallet authorizations (masked at the API layer per TASK-041)."""
    from app.services import pii_service

    db, ctx = await get_tenant_db(current_user, db)
    try:
        rows = await db.fetch(
            """
            SELECT instrument_id, blockchain, wallet_address, custody_type,
                   party_id, address_proof, proof_ref, authorized,
                   authorized_from, authorized_until, authorized_by, approved_by
            FROM app.wallet_authorization
            WHERE ($1::boolean IS FALSE OR authorized = TRUE)
            ORDER BY instrument_id
            """,
            only_authorized,
        )
    except Exception as e:
        raise database_error("onboarding.list_wallets", e)

    items = []
    for r in rows:
        item = dict(r)
        for k in ("authorized_from", "authorized_until"):
            if item.get(k) is not None:
                item[k] = item[k].isoformat()
        items.append(item)
    return {"status": "success",
            "wallets": pii_service.mask_pii(items, current_user["role"])}


def _public_verdict(verdict: dict) -> dict:
    return {k: verdict.get(k) for k in
            ("valid", "vct", "expiresAt", "reason", "evidence_hash")}


def _iso(value) -> Optional[str]:
    return value if isinstance(value, str) else None


def _json(value: dict) -> Optional[str]:
    import json as _json
    return _json.dumps(value) if value else None
