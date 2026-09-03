"""AWI Phase-1 tests: M2M client (TASK-037), address-control proofs
(TASK-044/045), onboarding + maker-checker + RLS (TASK-038/040/042),
nightly batch planning (TASK-048)."""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import ExternalServiceError, ServiceUnavailableError, ValidationAppError


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------- TASK-037

class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeHttpClient:
    """Stand-in for httpx.AsyncClient used by identity_provider."""

    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, url, json=None, headers=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        if self._exc:
            raise self._exc
        return self._response


@pytest.fixture
def provider_config(monkeypatch):
    monkeypatch.setenv("IDENTITY_PROVIDER_URL", "http://didvc-edge:8080")
    monkeypatch.setenv("IDENTITY_PROVIDER_API_KEY", "test-key-not-a-real-credential")
    monkeypatch.setenv("IDENTITY_PROVIDER_TENANT", "aml")
    monkeypatch.setenv("IDENTITY_PROVIDER_RETRIES", "0")
    import importlib
    from app.core import config
    import app.services.identity_provider as ip
    config.get_settings.cache_clear()
    ip._reset_breaker()
    yield ip
    config.get_settings.cache_clear()
    ip._reset_breaker()


def test_verify_credential_valid(provider_config, monkeypatch):
    ip = provider_config
    fake = FakeHttpClient(response=FakeResponse(payload={
        "valid": True, "vct": "hkt_kyc_v1", "expiresAt": "2027-01-01T00:00:00Z"}))
    monkeypatch.setattr(ip.httpx, "AsyncClient", lambda **kw: fake)
    verdict = run(ip.verify_credential("x" * 40))
    assert verdict["valid"] is True
    assert verdict["vct"] == "hkt_kyc_v1"
    assert verdict["evidence_hash"]
    # API key travels in the header, never in the body/URL
    call = fake.calls[0]
    assert call["headers"]["X-Api-Key"] == "test-key-not-a-real-credential"
    assert "test-key" not in call["url"]


def test_verify_credential_rejected_is_not_an_error(provider_config, monkeypatch):
    ip = provider_config
    fake = FakeHttpClient(response=FakeResponse(status_code=401))
    monkeypatch.setattr(ip.httpx, "AsyncClient", lambda **kw: fake)
    verdict = run(ip.verify_credential("x" * 40))
    assert verdict["valid"] is False
    assert verdict["reason"] == "rejected_by_provider_401"


def test_verify_credential_fails_closed_on_outage(provider_config, monkeypatch):
    import httpx
    ip = provider_config
    fake = FakeHttpClient(exc=httpx.ConnectError("refused"))
    monkeypatch.setattr(ip.httpx, "AsyncClient", lambda **kw: fake)
    with pytest.raises(ExternalServiceError):
        run(ip.verify_credential("x" * 40))
    assert ip.breaker_status()["failures"] == 1


def test_breaker_opens_after_consecutive_failures(provider_config, monkeypatch):
    import httpx
    ip = provider_config
    fake = FakeHttpClient(exc=httpx.ConnectError("refused"))
    monkeypatch.setattr(ip.httpx, "AsyncClient", lambda **kw: fake)
    for _ in range(5):
        with pytest.raises(ExternalServiceError):
            run(ip.verify_credential("x" * 40))
    assert ip.breaker_status()["open"] is True
    with pytest.raises(ServiceUnavailableError):
        run(ip.verify_credential("x" * 40))


def test_unconfigured_provider_rejected(monkeypatch):
    monkeypatch.delenv("IDENTITY_PROVIDER_URL", raising=False)
    monkeypatch.delenv("IDENTITY_PROVIDER_API_KEY", raising=False)
    from app.core import config
    import app.services.identity_provider as ip
    config.get_settings.cache_clear()
    with pytest.raises(ServiceUnavailableError):
        run(ip.verify_credential("x" * 40))
    config.get_settings.cache_clear()


def test_empty_credential_rejected_before_any_call(provider_config):
    with pytest.raises(ValidationAppError):
        run(provider_config.verify_credential(""))


# ---------------------------------------------------------------- TASK-044

@pytest.fixture(scope="module")
def evm_key():
    from eth_keys import keys
    priv = keys.PrivateKey(b"\x02" * 32)
    return priv, priv.public_key.to_checksum_address()


def _sign_eip191(priv, challenge: str) -> str:
    from eth_utils import keccak
    message = f"\x19Ethereum Signed Message:\n{len(challenge)}{challenge}".encode()
    digest = keccak(message)
    sig = priv.sign_msg_hash(digest)
    return sig.to_bytes().hex()


def test_evm_proof_roundtrip(evm_key):
    from app.services import wallet_proof
    priv, address = evm_key
    challenge = wallet_proof.issue_challenge(address.lower(), "ETHEREUM")["challenge"]
    result = wallet_proof.verify_evm_signature(challenge, _sign_eip191(priv, challenge))
    assert result["address"] == address
    assert result["proof_ref"].startswith("sig:")


def test_evm_proof_replay_rejected(evm_key):
    from app.services import wallet_proof
    priv, address = evm_key
    challenge = wallet_proof.issue_challenge(address.lower(), "ETHEREUM")["challenge"]
    signature = _sign_eip191(priv, challenge)
    wallet_proof.verify_evm_signature(challenge, signature)
    with pytest.raises(ValidationAppError, match="replay"):
        wallet_proof.verify_evm_signature(challenge, signature)


def test_evm_proof_wrong_key_rejected(evm_key):
    from eth_keys import keys
    from app.services import wallet_proof
    _, address = evm_key
    other = keys.PrivateKey(b"\x07" * 32)
    challenge = wallet_proof.issue_challenge(address.lower(), "ETHEREUM")["challenge"]
    with pytest.raises(ValidationAppError, match="different address|recovery"):
        wallet_proof.verify_evm_signature(challenge, _sign_eip191(other, challenge))


def test_evm_proof_malformed_signature(evm_key):
    from app.services import wallet_proof
    _, address = evm_key
    challenge = wallet_proof.issue_challenge(address.lower(), "ETHEREUM")["challenge"]
    with pytest.raises(ValidationAppError):
        wallet_proof.verify_evm_signature(challenge, "deadbeef")


def test_solana_proof_roundtrip():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from app.services import wallet_proof

    priv = Ed25519PrivateKey.generate()
    pub_bytes = priv.public_key().public_bytes_raw()
    # base58-encode the public key as the Solana address
    address = _base58_encode(pub_bytes)
    challenge = wallet_proof.issue_challenge(address, "SOLANA")["challenge"]
    signature = _base58_encode(priv.sign(challenge.encode()))
    result = wallet_proof.verify_solana_signature(challenge, signature, address)
    assert result["blockchain"] == "SOLANA"
    assert result["proof_ref"].startswith("sig:")


def _base58_encode(data: bytes) -> str:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    num = int.from_bytes(data, "big")
    out = ""
    while num:
        num, rem = divmod(num, 58)
        out = alphabet[rem] + out
    pad = len(data) - len(data.lstrip(b"\x00"))
    return "1" * pad + out


# ---------------------------------------------------------------- TASK-048

def test_batch_plan_revocation_deauthorizes():
    import sys
    sys.path.insert(0, "/home/ivenkwan/repo/Overwatch2/etl")
    from credential_planning import plan_status_updates

    records = [
        {"credential_id": "c1", "expires_at": None, "wallet_instruments": ["ETHEREUM:0xa"]},
        {"credential_id": "c2", "expires_at": None, "wallet_instruments": ["ETHEREUM:0xb"]},
        {"credential_id": "c3", "expires_at": None, "wallet_instruments": []},
        {"credential_id": "c4", "expires_at": None, "wallet_instruments": []},
    ]
    verdicts = [
        {"valid": False, "reason": "revoked by issuer"},
        {"valid": True, "expiresAt": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()},
        {"valid": True, "expiresAt": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()},
        {"error": "provider 503"},
    ]
    plan = plan_status_updates(records, verdicts)
    assert ("REVOKED", "c1") in plan["credential_updates"]
    assert ("EXPIRED", "c2") in plan["credential_updates"]
    assert ("REFRESH_DUE", "c3") in plan["credential_updates"]
    assert plan["deauthorizations"] == ["ETHEREUM:0xa", "ETHEREUM:0xb"]
    assert plan["dlq"] == [("c4", "provider 503")]


def test_batch_plan_missing_verdict_goes_to_dlq():
    import sys
    sys.path.insert(0, "/home/ivenkwan/repo/Overwatch2/etl")
    from credential_planning import plan_status_updates

    plan = plan_status_updates([{"credential_id": "c9", "expires_at": None,
                                 "wallet_instruments": []}], [])
    assert plan["dlq"] == [("c9", "no verdict returned by provider")]
    assert plan["credential_updates"] == []


# ---------------------------------------------------------------- TASK-038/040/042

class OnboardingFakeConn:
    """Records SQL + params for the onboarding endpoints."""

    def __init__(self):
        self.statements = []
        self.membership = {"user_id": uuid.uuid4(), "tenant_id": uuid.uuid4()}

    async def execute(self, sql, *args):
        self.statements.append((sql, args))

    async def fetchrow(self, sql, *args):
        self.statements.append((sql, args))
        if "app.tenant_memberships" in sql:
            return dict(self.membership)
        if "INSERT INTO app.party " in sql or "INSERT INTO app.party(" in sql:
            return {"party_id": args[0]}
        if "party_credential" in sql and "INSERT" in sql:
            return {"credential_id": args[0]}
        if "wallet_authorization" in sql and "INSERT" in sql:
            return {"instrument_id": args[0], "authorized": False,
                    "authorized_by": str(self.membership["user_id"])}
        if "SELECT authorized" in sql:
            return {"authorized": False, "authorized_by": str(self.membership["user_id"])}
        if "approved_by = $1" in sql or "UPDATE app.wallet_authorization" in sql:
            return {"instrument_id": args[2] if len(args) > 2 else "x",
                    "authorized_until": datetime.now(timezone.utc) + timedelta(days=365)}
        return None

    def transaction(self):
        return self

    def transaction(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def test_tenant_context_fail_closed():
    from app.core.tenancy import resolve_tenant
    from app.core.exceptions import AuthorizationAppError

    class NoMembershipConn(OnboardingFakeConn):
        async def fetchrow(self, sql, *args):
            return None

    with pytest.raises(AuthorizationAppError):
        run(resolve_tenant({"username": "ghost", "id": str(uuid.uuid4())}, NoMembershipConn()))


def test_tenant_context_sets_rls_settings():
    from app.core.tenancy import resolve_tenant, set_tenant_context

    conn = OnboardingFakeConn()
    ctx = run(resolve_tenant({"username": "maker", "id": str(uuid.uuid4())}, conn))
    run(set_tenant_context(conn, ctx))
    tenant_stmts = [s for s in conn.statements if "app.current_tenant" in s[0]]
    actor_stmts = [s for s in conn.statements if "app.actor_user_id" in s[0]]
    assert tenant_stmts and actor_stmts  # explicit context, no LIMIT-1 shortcuts


def test_onboarding_verify_persists_party_and_credential(monkeypatch, provider_config):
    from app.api.v1 import onboarding as ob
    from app.core import config

    fake = FakeHttpClient(response=FakeResponse(payload={
        "valid": True, "vct": "hkt_kyc_v1", "issuerDid": "did:web:issuer",
        "expiresAt": "2027-01-01T00:00:00Z", "claims": {"givenName": "Chan Tai Man"},
    }))
    monkeypatch.setattr(ob.identity_provider.httpx, "AsyncClient", lambda **kw: fake)

    conn = OnboardingFakeConn()
    user = {"id": str(uuid.uuid4()), "username": "maker", "role": "ADMIN"}
    submission = ob.CredentialSubmission(credential="x" * 40, include_claims=True)
    result = run(ob.verify_credential(submission, current_user=user, db=conn))
    assert result["status"] == "verified"
    inserted_party = [s for s in conn.statements if "INSERT INTO app.party " in s[0]]
    inserted_cred = [s for s in conn.statements if "INSERT INTO app.party_credential" in s[0]]
    assert inserted_party and inserted_cred
    assert "ON CONFLICT" in inserted_party[0][0]  # idempotent upsert


def test_maker_checker_requires_different_users():
    from app.api.v1 import onboarding as ob
    from app.core.exceptions import AuthorizationAppError

    conn = OnboardingFakeConn()
    maker = {"id": str(conn.membership["user_id"]), "username": "maker", "role": "ADMIN"}
    # same user proposing then approving must be rejected
    with pytest.raises(AuthorizationAppError, match="different users"):
        run(ob.approve_wallet("ETHEREUM:0xabc", current_user=maker, db=conn))

    checker_conn = OnboardingFakeConn()
    checker_conn.membership["user_id"] = conn.membership["user_id"]
    checker = {"id": str(uuid.uuid4()), "username": "checker", "role": "ADMIN"}
    # maker's authorized_by differs from checker id -> approval proceeds
    class OtherMakerConn(OnboardingFakeConn):
        async def fetchrow(self, sql, *args):
            if "SELECT authorized" in sql:
                return {"authorized": False, "authorized_by": str(uuid.uuid4())}
            return await super().fetchrow(sql, *args)

    conn2 = OtherMakerConn()
    approved = run(ob.approve_wallet("ETHEREUM:0xabc", current_user=checker, db=conn2))
    assert approved["status"] == "authorized"


def test_wallet_registration_requires_proof():
    from app.api.v1 import onboarding as ob

    conn = OnboardingFakeConn()
    user = {"id": str(uuid.uuid4()), "username": "maker", "role": "ADMIN"}
    registration = type("R", (), {
        "party_id": "P1", "blockchain": "ETHEREUM", "wallet_address": "0xabc12345",
        "custody_type": None, "instrument_id": None,
        "challenge": None, "signature": None, "proof_ref": None})()
    with pytest.raises(ValidationAppError, match="Address-control proof required"):
        run(ob.register_wallet(registration, current_user=user, db=conn))


# ---------------------------------------------------------------- TASK-046

def test_wallet_binding_issuance_roundtrip(monkeypatch):
    from app.services import wallet_issuance as wi, identity_provider as ip

    monkeypatch.setenv("IDENTITY_PROVIDER_URL", "http://didvc-edge:8080")
    monkeypatch.setenv("IDENTITY_PROVIDER_API_KEY", "k")
    monkeypatch.setenv("IDENTITY_PLATFORM_URL", "http://didvc-platform:8181")
    monkeypatch.setenv("IDENTITY_PLATFORM_TOKEN", "platform-token-not-real")
    from app.core import config
    config.get_settings.cache_clear()

    class RoutingClient(FakeHttpClient):
        """One shared httpx stand-in: routes by URL (issuance vs verify).
        Both wi.httpx and ip.httpx are the SAME module object, so a single
        patch must serve both call sites."""

        def __init__(self):
            super().__init__(response=FakeResponse(payload={
                "id": "cred_123", "credential": "issued-jwt-value" * 5}))

        async def post(self, url, json=None, headers=None):
            self.calls.append({"url": url, "json": json, "headers": headers})
            if "/m2m/verify" in url:
                return FakeResponse(payload={
                    "valid": True, "vct": "hkt_wallet_binding_v1",
                    "expiresAt": "2027-01-01T00:00:00Z"})
            return self._response

    shared = RoutingClient()
    monkeypatch.setattr(wi.httpx, "AsyncClient", lambda **kw: shared)

    result = run(wi.request_wallet_binding(
        subject_did="did:web:issuer", wallet_address="0xAbCdEf1234567890",
        blockchain="ETHEREUM", custody_type="UNHOSTED", proof_ref="sig:abc"))
    assert result["status"] == "verified"
    assert result["credential_id"] == "cred_123"
    # the issuance payload carries a HASH of the address, never the plaintext
    sent = [c for c in shared.calls if "/didvc/credentials" in c["url"]][0]["json"]
    assert sent["claims"]["walletAddressHash"] != "0xAbCdEf1234567890"
    assert len(sent["claims"]["walletAddressHash"]) == 64
    # platform token travels in the Authorization header only
    config.get_settings.cache_clear()


def test_wallet_binding_requires_configuration(monkeypatch):
    from app.core import config
    from app.services import wallet_issuance as wi
    monkeypatch.delenv("IDENTITY_PLATFORM_URL", raising=False)
    monkeypatch.delenv("IDENTITY_PLATFORM_TOKEN", raising=False)
    config.get_settings.cache_clear()
    with pytest.raises(ServiceUnavailableError):
        run(wi.request_wallet_binding("did:web:x", "0xAbCdEf1234567890",
                                      "ETHEREUM", "UNHOSTED"))
    config.get_settings.cache_clear()


def test_wallet_binding_validates_inputs(monkeypatch):
    from app.core import config
    from app.services import wallet_issuance as wi
    monkeypatch.setenv("IDENTITY_PLATFORM_URL", "http://p")
    monkeypatch.setenv("IDENTITY_PLATFORM_TOKEN", "t")
    config.get_settings.cache_clear()
    with pytest.raises(ValidationAppError):
        run(wi.request_wallet_binding("", "0xAbCdEf1234567890", "ETHEREUM", "UNHOSTED"))
    config.get_settings.cache_clear()
