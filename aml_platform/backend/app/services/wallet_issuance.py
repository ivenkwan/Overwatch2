"""
Wallet-binding credential issuance client (AWI TASK-046, first-party).

After a KYC/KYB verification and a successful address-control proof, this
client asks the didvc platform to issue an `hkt_wallet_binding_v1` credential
binding subject DID <-> hashed wallet address <-> custody type. The AML side
never signs anything: issuance stays with the accredited (first-party)
issuer, and the binding is verified afterwards through the same M2M path.

The platform admin token comes exclusively from the environment
(IDENTITY_PLATFORM_TOKEN) — no literals.
"""

from typing import Optional

import httpx

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError, ServiceUnavailableError, ValidationAppError

BINDING_VCT = "hkt_wallet_binding_v1"


async def request_wallet_binding(
    subject_did: str,
    wallet_address: str,
    blockchain: str,
    custody_type: str,
    binding_level: str = "ADDRESS_PROOF_VERIFIED",
    proof_ref: Optional[str] = None,
    valid_until: Optional[str] = None,
    include_claims: bool = False,
) -> dict:
    """Issue a first-party wallet-binding credential and verify it back.

    Returns {status: issued|verified, credential_id?, verdict} where verdict
    carries the M2M verification outcome including its evidence hash.
    """
    from app.services import identity_provider

    settings = get_settings()
    platform_url = settings.identity_platform_url
    token = settings.identity_platform_token
    if not platform_url or not token:
        raise ServiceUnavailableError(
            "Identity platform not configured (IDENTITY_PLATFORM_URL / IDENTITY_PLATFORM_TOKEN)"
        )
    for value, name in ((subject_did, "subject_did"), (wallet_address, "wallet_address"),
                        (blockchain, "blockchain"), (custody_type, "custody_type")):
        if not value or not isinstance(value, str) or len(value) > 255:
            raise ValidationAppError(f"invalid {name}")

    import hashlib
    address_hash = hashlib.sha256(wallet_address.lower().encode()).hexdigest()

    payload = {
        "vct": BINDING_VCT,
        "subjectDid": subject_did,
        "claims": {
            "walletAddressHash": address_hash,
            "blockchain": blockchain,
            "custodyType": custody_type,
            "bindingLevel": binding_level,
            "validUntil": valid_until,
            **({"proofRef": proof_ref} if proof_ref else {}),
        },
    }

    try:
        async with httpx.AsyncClient(timeout=settings.identity_provider_timeout) as client:
            response = await client.post(
                f"{platform_url.rstrip('/')}/didvc/credentials",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError as exc:
        raise ExternalServiceError("Identity platform unreachable") from exc
    if response.status_code >= 400:
        raise ExternalServiceError(
            "Identity platform rejected the issuance request",
            details={"status": response.status_code},
        )

    issuance = response.json()
    credential = issuance.get("credential")
    if not credential:
        raise ExternalServiceError("Identity platform returned no credential")

    verdict = await identity_provider.verify_credential(credential, include_claims=include_claims)
    return {"status": "verified" if verdict.get("valid") else "issued_unverified",
            "credential_id": issuance.get("id"),
            "verdict": verdict}
