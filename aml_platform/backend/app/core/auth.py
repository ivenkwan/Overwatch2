"""
Authentication & authorization (TASK-001 / TASK-002).

Security model:
  * AUTH_MODE=keycloak (default) — Keycloak-issued RS256 access tokens are
    validated against the realm JWKS with issuer, expiry and audience checks
    (see app.core.keycloak_auth). This is the production path.
  * AUTH_MODE=local — HS256 tokens signed with the JWT_SECRET_KEY environment
    variable (required, min 32 chars, weak values rejected). Development and
    test path only.

There is deliberately NO unauthenticated fallback: a request without a valid
Bearer token is rejected with 401 (the former hardcoded anonymous-admin
bypass has been removed).
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from app.core.config import (
    AUTH_MODE_KEYCLOAK,
    AUTH_MODE_LOCAL,
    Settings,
    get_settings,
)
from app.core.keycloak_auth import KeycloakTokenValidator, KeycloakValidationError

audit_logger = logging.getLogger("aml_audit")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)

# Built lazily because Settings validation happens at startup.
_keycloak_validator: Optional[KeycloakTokenValidator] = None


def _settings() -> Settings:
    return get_settings()


def _keycloak() -> KeycloakTokenValidator:
    global _keycloak_validator
    if _keycloak_validator is None:
        _keycloak_validator = KeycloakTokenValidator(_settings())
    return _keycloak_validator


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Issue a local HS256 token (AUTH_MODE=local only)."""
    settings = _settings()
    if settings.auth_mode != AUTH_MODE_LOCAL:
        raise RuntimeError("Local token issuance is disabled when AUTH_MODE != local")
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm="HS256")


def _unauthorized(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    token: Optional[str] = Security(oauth2_scheme),
    request: Request = None,
) -> dict:
    """Validate the access token (Authorization header OR the httpOnly
    session cookie) and return the acting user, or raise 401.

    Fail-closed: missing, malformed, expired, wrongly-signed or
    wrong-audience tokens are all rejected. Anonymous access is not
    permitted.
    """
    if not token and request is not None:
        token = request.cookies.get("aml_session")
    if not token:
        raise _unauthorized("Not authenticated: Bearer token or session cookie required")

    settings = _settings()
    credentials_exception = _unauthorized()

    if settings.auth_mode == AUTH_MODE_KEYCLOAK:
        try:
            return _keycloak().validate_token(token)
        except KeycloakValidationError as exc:
            audit_logger.warning("Rejected token (keycloak mode): %s", exc)
            raise credentials_exception from exc

    # Local HS256 mode (development/tests)
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:
        raise credentials_exception

    username = payload.get("sub")
    role = payload.get("role")
    user_id = payload.get("id")
    if username is None or role is None or user_id is None:
        raise credentials_exception

    scopes = ["alert.read"]
    if role in ("SENIOR_INVESTIGATOR", "ADMIN", "DEPARTMENT_HEAD"):
        scopes.append("graph.explore")

    return {"id": str(user_id), "username": username, "role": role, "scopes": scopes}


def get_current_user_with_scope(required_scope: str):
    """Scope-based RBAC enforcement on top of get_current_user."""

    def scope_checker(user: dict = Depends(get_current_user)):
        if required_scope not in user.get("scopes", []):
            if required_scope not in [user.get("role"), "ANY"]:
                raise HTTPException(status_code=403, detail=f"Insufficient permissions for {required_scope}")
        return user

    return scope_checker


def require_role(*roles: str):
    """Role-based enforcement: allow only the given platform roles."""

    def role_checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Requires one of roles {list(roles)} (you are {user.get('role')})",
            )
        return user

    return role_checker


async def log_audit_event(user, action: str, details: Optional[str] = None, **kwargs) -> bool:
    """Persist an audit event to the tamper-evident table (never raises).

    `user` may be a user dict (from get_current_user) or a bare id string —
    callers that only have an id keep working.
    """
    from app.services import audit_service

    if isinstance(user, dict):
        return await audit_service.record_audit_event(action, actor=user, reason=details, **kwargs)
    return await audit_service.record_audit_event(action, actor_id=str(user), reason=details, **kwargs)
