"""
Keycloak access-token validation (TASK-002).

Validates Keycloak-issued JWTs the way a relying party should:
  * RS256 signature verified against the realm JWKS (cached, PyJWKClient)
  * issuer (`iss`) must equal the configured realm issuer
  * expiry (`exp`) and not-before (`nbf`) enforced, with configurable leeway
  * audience (`aud`) / authorized-party (`azp`) must match the expected client
  * realm roles are mapped onto platform roles (aml_admin -> ADMIN, ...)

The validator fails closed: any error (network, unknown `kid`, bad signature,
expired token, wrong issuer/audience) results in an authentication failure.
"""

import logging
from typing import Any, Optional

import jwt
from jwt import PyJWKClient

from app.core.config import Settings

logger = logging.getLogger("aml_auth")

# Keycloak realm role -> platform role, in precedence order (first match wins).
REALM_ROLE_TO_PLATFORM_ROLE = [
    ("aml_admin", "ADMIN"),
    ("aml_department_head", "DEPARTMENT_HEAD"),
    ("aml_senior_investigator", "SENIOR_INVESTIGATOR"),
    ("aml_analyst", "JUNIOR_ANALYST"),
]

DEFAULT_ROLE = "JUNIOR_ANALYST"

TOKEN_ALGORITHMS = ["RS256"]


class KeycloakValidationError(Exception):
    """Raised when a token cannot be validated (fail-closed)."""


class KeycloakTokenValidator:
    def __init__(self, settings: Settings, jwks_client: Optional[PyJWKClient] = None) -> None:
        self._settings = settings
        self._jwks_client = jwks_client or PyJWKClient(
            settings.keycloak_jwks_url,
            cache_keys=True,
            # Refresh cached JWKS at most once per 10 minutes per signing key set.
            lifespan=600,
        )

    def validate_token(self, token: str) -> dict[str, Any]:
        """Validate a Keycloak access token and return the mapped user dict."""
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=TOKEN_ALGORITHMS,
                issuer=self._settings.keycloak_issuer,
                leeway=self._settings.keycloak_leeway_seconds,
                options={
                    "require": ["exp", "iss", "sub"],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_iss": True,
                    # aud/azp verified manually below: Keycloak access tokens
                    # legitimately carry either aud, azp, or both.
                    "verify_aud": False,
                },
            )
        except jwt.PyJWTError as exc:
            raise KeycloakValidationError(f"Token rejected by Keycloak validation: {exc}") from exc
        except Exception as exc:  # network/JWKS failures — fail closed
            raise KeycloakValidationError(f"Could not validate token against Keycloak: {exc}") from exc

        self._verify_audience(payload)

        role = self._map_role(payload)
        username = payload.get("preferred_username") or payload.get("sub")
        scopes = ["alert.read"]
        if role in ("SENIOR_INVESTIGATOR", "ADMIN", "DEPARTMENT_HEAD"):
            scopes.append("graph.explore")

        return {
            "id": payload.get("sub"),
            "username": username,
            "role": role,
            "scopes": scopes,
            "claims": payload,
        }

    def _verify_audience(self, payload: dict[str, Any]) -> None:
        expected = self._settings.keycloak_audience
        aud = payload.get("aud")
        azp = payload.get("azp")

        if isinstance(aud, str):
            aud = [aud]
        audience_ok = bool(aud) and expected in aud
        azp_ok = azp == expected

        if not (audience_ok or azp_ok):
            raise KeycloakValidationError(
                f"Token audience/azp does not match expected client '{expected}' "
                f"(aud={aud!r}, azp={azp!r})"
            )

    def _map_role(self, payload: dict[str, Any]) -> str:
        realm_roles = (payload.get("realm_access") or {}).get("roles") or []

        for realm_role, platform_role in REALM_ROLE_TO_PLATFORM_ROLE:
            if realm_role in realm_roles:
                return platform_role

        # Client roles (resource_access.<client>.roles) as a secondary source.
        resource_access = payload.get("resource_access") or {}
        if isinstance(resource_access, dict):
            for client_entry in resource_access.values():
                client_roles = (client_entry or {}).get("roles") or []
                for realm_role, platform_role in REALM_ROLE_TO_PLATFORM_ROLE:
                    if realm_role in client_roles:
                        return platform_role

        return DEFAULT_ROLE
