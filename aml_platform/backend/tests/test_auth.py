"""
TASK-002: authentication behaviour.

Covers: no-token rejection (anonymous bypass removed), local HS256 token
validation, scope/role enforcement, and the Keycloak RS256 validator
(signature, expiry, issuer, audience) using locally generated RSA keys.
"""

import asyncio
import types
from datetime import datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core import auth
from app.core.config import AUTH_MODE_LOCAL, get_settings
from app.core.keycloak_auth import KeycloakTokenValidator, KeycloakValidationError

TEST_SECRET = "t" * 48


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def local_mode(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", AUTH_MODE_LOCAL)
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)
    get_settings.cache_clear()
    auth._keycloak_validator = None
    yield
    get_settings.cache_clear()
    auth._keycloak_validator = None


def make_local_token(claims=None, secret=TEST_SECRET):
    payload = {"sub": "analyst_01", "role": "JUNIOR_ANALYST", "id": 7,
               "exp": datetime.utcnow() + timedelta(minutes=5)}
    payload.update(claims or {})
    return jwt.encode(payload, secret, algorithm="HS256")


# --- Anonymous bypass removed -------------------------------------------------

def test_missing_token_rejected(local_mode):
    with pytest.raises(Exception) as exc_info:
        run(auth.get_current_user(None))
    assert exc_info.value.status_code == 401


def test_no_hardcoded_admin_fallback(local_mode):
    """The old bypass returned a fixed admin dict for anonymous calls."""
    with pytest.raises(Exception) as exc_info:
        run(auth.get_current_user(None))
    assert exc_info.value.status_code == 401


# --- Local HS256 mode ----------------------------------------------------------

def test_valid_local_token(local_mode):
    token = make_local_token()
    user = run(auth.get_current_user(token))
    assert user["username"] == "analyst_01"
    assert user["role"] == "JUNIOR_ANALYST"
    assert user["scopes"] == ["alert.read"]


def test_senior_role_gets_graph_scope(local_mode):
    token = make_local_token({"role": "SENIOR_INVESTIGATOR"})
    user = run(auth.get_current_user(token))
    assert "graph.explore" in user["scopes"]


def test_tampered_signature_rejected(local_mode):
    token = make_local_token(secret=TEST_SECRET + "x" * 48)
    with pytest.raises(Exception) as exc_info:
        run(auth.get_current_user(token))
    assert exc_info.value.status_code == 401


def test_expired_token_rejected(local_mode):
    token = make_local_token({"exp": datetime.utcnow() - timedelta(minutes=1)})
    with pytest.raises(Exception) as exc_info:
        run(auth.get_current_user(token))
    assert exc_info.value.status_code == 401


def test_token_missing_claims_rejected(local_mode):
    token = jwt.encode({"exp": datetime.utcnow() + timedelta(minutes=5)}, TEST_SECRET, algorithm="HS256")
    with pytest.raises(Exception) as exc_info:
        run(auth.get_current_user(token))
    assert exc_info.value.status_code == 401


# --- Scope / role enforcement ---------------------------------------------------

def test_scope_checker_forbids_missing_scope(local_mode):
    token = make_local_token()
    user = run(auth.get_current_user(token))
    checker = auth.get_current_user_with_scope("graph.explore")
    with pytest.raises(Exception) as exc_info:
        checker(user=user)
    assert exc_info.value.status_code == 403


def test_scope_checker_allows_matching_scope(local_mode):
    token = make_local_token({"role": "SENIOR_INVESTIGATOR"})
    user = run(auth.get_current_user(token))
    checker = auth.get_current_user_with_scope("graph.explore")
    assert checker(user=user)["username"] == "analyst_01"


def test_require_role(local_mode):
    token = make_local_token({"role": "JUNIOR_ANALYST"})
    analyst = run(auth.get_current_user(token))
    admin = run(auth.get_current_user(make_local_token({"role": "ADMIN"})))

    with pytest.raises(Exception) as exc_info:
        auth.require_role("ADMIN")(user=analyst)
    assert exc_info.value.status_code == 403
    assert auth.require_role("ADMIN")(user=admin)["role"] == "ADMIN"


def test_local_token_issuance_disabled_in_keycloak_mode(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "keycloak")
    monkeypatch.setenv("KEYCLOAK_URL", "http://keycloak:8080")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError):
        auth.create_access_token({"sub": "x"})


# --- Keycloak RS256 validator ---------------------------------------------------

class StaticJWKS:
    """Stands in for jwt.PyJWKClient: always serves the given public key."""

    def __init__(self, public_key):
        self._key = public_key

    def get_signing_key_from_jwt(self, token):
        return types.SimpleNamespace(key=self._key)


@pytest.fixture(scope="module")
def rsa_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def kc_settings(monkeypatch, **over):
    import os

    env = {
        "AUTH_MODE": "keycloak",
        "KEYCLOAK_URL": "http://keycloak:8080",
        "KEYCLOAK_REALM": "aml",
        "KEYCLOAK_AUDIENCE": "aml-portal",
    }
    env.update(over)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    from app.core.config import Settings

    return Settings()


def kc_token(private_key, claims=None, kid="test-key"):
    import time

    payload = {
        "iss": "http://keycloak:8080/realms/aml",
        "sub": "11111111-1111-1111-1111-111111111111",
        "preferred_username": "kc_user",
        "azp": "aml-portal",
        "realm_access": {"roles": ["aml_senior_investigator"]},
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
    }
    payload.update(claims or {})
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": kid})


def test_keycloak_valid_token_maps_roles(monkeypatch, rsa_pair):
    private_key, public_key = rsa_pair
    validator = KeycloakTokenValidator(kc_settings(monkeypatch), jwks_client=StaticJWKS(public_key))
    user = validator.validate_token(kc_token(private_key))
    assert user["role"] == "SENIOR_INVESTIGATOR"
    assert user["username"] == "kc_user"
    assert "graph.explore" in user["scopes"]


def test_keycloak_expired_token_rejected(monkeypatch, rsa_pair):
    private_key, public_key = rsa_pair
    validator = KeycloakTokenValidator(kc_settings(monkeypatch), jwks_client=StaticJWKS(public_key))
    expired = kc_token(private_key, claims={"exp": int(datetime.utcnow().timestamp()) - 3600})
    with pytest.raises(KeycloakValidationError):
        validator.validate_token(expired)


def test_keycloak_wrong_issuer_rejected(monkeypatch, rsa_pair):
    private_key, public_key = rsa_pair
    validator = KeycloakTokenValidator(kc_settings(monkeypatch), jwks_client=StaticJWKS(public_key))
    forged = kc_token(private_key, claims={"iss": "http://evil.example/realms/aml"})
    with pytest.raises(KeycloakValidationError):
        validator.validate_token(forged)


def test_keycloak_wrong_audience_rejected(monkeypatch, rsa_pair):
    private_key, public_key = rsa_pair
    validator = KeycloakTokenValidator(kc_settings(monkeypatch), jwks_client=StaticJWKS(public_key))
    wrong_client = kc_token(private_key, claims={"azp": "other-client", "aud": "other-client"})
    with pytest.raises(KeycloakValidationError):
        validator.validate_token(wrong_client)


def test_keycloak_wrong_signature_rejected(monkeypatch, rsa_pair):
    private_key, _ = rsa_pair
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    validator = KeycloakTokenValidator(
        kc_settings(monkeypatch), jwks_client=StaticJWKS(attacker_key.public_key())
    )
    with pytest.raises(KeycloakValidationError):
        validator.validate_token(kc_token(private_key))


def test_keycloak_admin_role_precedence(monkeypatch, rsa_pair):
    private_key, public_key = rsa_pair
    validator = KeycloakTokenValidator(kc_settings(monkeypatch), jwks_client=StaticJWKS(public_key))
    token = kc_token(
        private_key,
        claims={"realm_access": {"roles": ["aml_analyst", "aml_admin"]}},
    )
    assert validator.validate_token(token)["role"] == "ADMIN"


def test_keycloak_unknown_role_defaults_to_analyst(monkeypatch, rsa_pair):
    private_key, public_key = rsa_pair
    validator = KeycloakTokenValidator(kc_settings(monkeypatch), jwks_client=StaticJWKS(public_key))
    token = kc_token(private_key, claims={"realm_access": {"roles": ["some_other_role"]}})
    assert validator.validate_token(token)["role"] == "JUNIOR_ANALYST"
