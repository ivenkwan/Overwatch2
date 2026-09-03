"""
E2E: authorized-wallet identity provider roundtrip (AWI TASK-059).

Drives a LIVE didvc-edge (demo pilot profile) exactly the way the AML
platform's identity_provider client will:

  1. fail-closed behaviour: M2M closed without a key; garbage credentials
     verify to valid=false (never an error page);
  2. full issuance roundtrip: internal offer -> pre-authorized code ->
     access token -> credential (Ed25519 proof with the issuer audience) ->
     M2M verify -> valid=true with vct + expiry;
  3. trust enforcement: the seeded tenant (bank-a) accepts the demo issuer;
     an unregistered tenant (aml) rejects the same credential — precisely
     what TASK-033's trust registration changes.

Setup (keys are generated per boot — never committed):
      scripts/run_didvc_edge_pilot.sh          # exports DIDVC_EDGE_* env
      pytest tests/e2e -v
Env:  DIDVC_EDGE_URL (default http://127.0.0.1:8090),
      DIDVC_EDGE_INTERNAL_API_KEY, DIDVC_EDGE_M2M_API_KEYS (required;
      the suite skips when the pilot is not running or keys are unset).
"""

import base64
import json
import os
import time

import httpx
import pytest

EDGE = os.environ.get("DIDVC_EDGE_URL", "http://127.0.0.1:8090").rstrip("/")
TENANT_SEEDED = "bank-a"          # demo platform seeds trust for this tenant
TENANT_AML = "aml"                # the AML platform tenant (TASK-033 pilot registration)
TENANT_UNREGISTERED = "not-registered-anywhere"
INTERNAL_KEY = os.environ.get("DIDVC_EDGE_INTERNAL_API_KEY", "")
M2M_KEY = os.environ.get("DIDVC_EDGE_M2M_API_KEYS", "").split(",")[0]


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _pilot_ready() -> bool:
    return bool(INTERNAL_KEY and M2M_KEY)


@pytest.fixture(scope="session")
def edge_up() -> bool:
    if not _pilot_ready():
        pytest.skip("DIDVC_EDGE_INTERNAL_API_KEY / DIDVC_EDGE_M2M_API_KEYS not set "
                    "(run scripts/run_didvc_edge_pilot.sh)")
    try:
        return httpx.get(f"{EDGE}/demo/issuer-kid", timeout=5).status_code == 200
    except httpx.HTTPError:
        pytest.skip(f"didvc-edge pilot not reachable at {EDGE}")


@pytest.fixture(scope="session")
def issuer_kid(edge_up) -> dict:
    return httpx.get(f"{EDGE}/demo/issuer-kid", timeout=5).json()


@pytest.fixture(scope="session")
def credential_issuer(edge_up) -> str:
    """The advertised credential issuer — the audience proofs must carry
    (F-8). Discovered from metadata exactly like a conformant wallet."""
    metadata = httpx.get(f"{EDGE}/{TENANT_SEEDED}/.well-known/openid-credential-issuer",
                         timeout=5).json()
    return metadata["credential_issuer"]


@pytest.fixture(scope="session")
def issued_credential(issuer_kid, credential_issuer) -> str:
    """Full OID4VCI pre-authorized roundtrip: offer -> token -> credential."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    offer_body = {
        "schemaId": "hkt-kyc-v1",
        "subjectId": "e2e-subject-001",
        "kid": issuer_kid["kid"],
        "alwaysDisclosedClaims": {"kycLevel": "REMOTE_FULL"},
        "selectivelyDisclosedClaims": {"givenName": "E2E", "nationality": "HK"},
    }
    offer = httpx.post(
        f"{EDGE}/{TENANT_SEEDED}/internal/offers",
        json=offer_body,
        headers={"X-Api-Key": INTERNAL_KEY},
        timeout=10,
    )
    assert offer.status_code == 200, offer.text

    pre_auth_code = offer.json()["grants"][
        "urn:ietf:params:oauth:grant-type:pre-authorized_code"]["pre-authorized_code"]

    token = httpx.post(
        f"{EDGE}/{TENANT_SEEDED}/token",
        data={"grant_type": "urn:ietf:params:oauth:grant-type:pre-authorized_code",
              "pre-authorized_code": pre_auth_code},
        timeout=10,
    )
    assert token.status_code == 200, token.text
    c_nonce = token.json()["c_nonce"]

    # openid4vci-proof+jwt with the wallet's Ed25519 key; aud = the
    # advertised credential issuer per F-8 (discovered from metadata).
    holder = Ed25519PrivateKey.generate()
    public = holder.public_key().public_bytes_raw()
    header = {"typ": "openid4vci-proof+jwt", "alg": "EdDSA",
              "jwk": {"kty": "OKP", "crv": "Ed25519", "x": _b64url(public)}}
    payload = {"iss": "e2e-wallet", "aud": credential_issuer,
               "iat": int(time.time()), "nonce": c_nonce}
    signing_input = f"{_b64url(json.dumps(header).encode())}.{_b64url(json.dumps(payload).encode())}"
    signature = holder.sign(signing_input.encode())
    proof_jwt = f"{signing_input}.{_b64url(signature)}"

    credential = httpx.post(
        f"{EDGE}/{TENANT_SEEDED}/credential",
        json={"format": "dc+sd-jwt", "vct": "hkt_kyc_v1",
              "proof": {"proof_type": "jwt", "jwt": proof_jwt}},
        headers={"Authorization": f"Bearer {token.json()['access_token']}"},
        timeout=10,
    )
    assert credential.status_code == 200, credential.text
    return credential.json()["credential"]


# ---------------------------------------------------------------- 1. fail-closed

def test_m2m_rejects_missing_api_key(edge_up):
    assert edge_up
    response = httpx.post(
        f"{EDGE}/{TENANT_SEEDED}/m2m/verify",
        json={"credential": "not-a-real-credential"},
        timeout=10,
    )
    assert response.status_code == 401


def test_m2m_garbage_credential_fails_closed(edge_up):
    assert edge_up
    response = httpx.post(
        f"{EDGE}/{TENANT_SEEDED}/m2m/verify",
        json={"credential": "garbage.credential.value"},
        headers={"X-Api-Key": M2M_KEY},
        timeout=10,
    )
    assert response.status_code == 200
    verdict = response.json()
    assert verdict.get("valid") is False
    assert verdict.get("reason")


def test_internal_offers_requires_admin_key(edge_up):
    assert edge_up
    response = httpx.post(
        f"{EDGE}/{TENANT_SEEDED}/internal/offers",
        json={"schemaId": "hkt-kyc-v1", "subjectId": "x", "kid": "k"},
        headers={"X-Api-Key": INTERNAL_KEY + "-wrong"},  # derived wrong key
        timeout=10,
    )
    assert response.status_code == 401


# ---------------------------------------------------------------- 2. roundtrip

def test_issued_credential_verifies_via_m2m(issued_credential):
    response = httpx.post(
        f"{EDGE}/{TENANT_SEEDED}/m2m/verify",
        json={"credential": issued_credential, "includeClaims": False},
        headers={"X-Api-Key": M2M_KEY},
        timeout=10,
    )
    assert response.status_code == 200
    verdict = response.json()
    assert verdict.get("valid") is True, verdict
    assert verdict.get("vct") == "hkt_kyc_v1"
    assert verdict.get("expiresAt")


def test_batch_verify_roundtrip(issued_credential):
    # Batch contract: {"records": [{id, credential}, ...]} — each entry gets
    # its own verdict; a well-formed-but-fake JWT fails closed per record.
    response = httpx.post(
        f"{EDGE}/{TENANT_SEEDED}/m2m/verify-batch",
        json={"records": [
            {"id": "r1", "credential": issued_credential},
            {"id": "r2", "credential": "eyJhbGciOiJFZERTQSJ9.eyJ2Y3QiOiJmYWtlIn0.ZmFrZQ"},
        ]},
        headers={"X-Api-Key": M2M_KEY},
        timeout=10,
    )
    assert response.status_code == 200, response.text
    results = response.json().get("results", [])
    assert len(results) == 2
    by_id = {r.get("id"): r for r in results}
    assert by_id["r1"].get("valid") is True
    assert by_id["r2"].get("valid") is False


# ---------------------------------------------------------------- 3. trust gate

def test_aml_tenant_accepts_after_registration(issued_credential):
    """TASK-033 (pilot): the AML relying tenant is registered against the
    first-party issuer, so its credentials verify through the M2M seam."""
    response = httpx.post(
        f"{EDGE}/{TENANT_AML}/m2m/verify",
        json={"credential": issued_credential},
        headers={"X-Api-Key": M2M_KEY},
        timeout=10,
    )
    assert response.status_code == 200
    assert response.json().get("valid") is True


def test_unregistered_tenant_rejects_the_same_credential(issued_credential):
    """Trust enforcement: an unregistered tenant rejects the identical
    credential — the M2M seam enforces the trust registry, so tenant
    registration is a real security boundary."""
    response = httpx.post(
        f"{EDGE}/{TENANT_UNREGISTERED}/m2m/verify",
        json={"credential": issued_credential},
        headers={"X-Api-Key": M2M_KEY},
        timeout=10,
    )
    verdict = response.json()
    assert verdict.get("valid") is False
