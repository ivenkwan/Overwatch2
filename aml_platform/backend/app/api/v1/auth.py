"""
Login endpoint.

AUTH_MODE=local (development): authenticates against the local `public.users`
table and issues an HS256 token signed with JWT_SECRET_KEY.

AUTH_MODE=keycloak (production default): proxies the resource-owner password
grant to Keycloak and returns the Keycloak-issued access token. The backend
never sees or stores the password beyond forwarding this single request.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core import auth
from app.core.config import AUTH_MODE_KEYCLOAK, get_settings
from app.schemas.user import Token
from app.db.session import get_db
from app.services import audit_service

router = APIRouter()

COOKIE_NAME = "aml_session"
COOKIE_MAX_AGE = 60 * 60 * 12  # 12h session


def _set_session_cookie(response: Response, access_token: str) -> None:
    """Set the httpOnly session cookie carrying the access token (the
    browser session client relies on it — no token in localStorage)."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=False,          # terminate TLS at the ingress; flip via env in prod
        samesite="lax",
        path="/",
    )


async def _keycloak_password_grant(username: str, password: str) -> dict:
    """Exchange credentials for a Keycloak access token (ROPC grant)."""
    import requests

    settings = get_settings()
    token_url = f"{settings.keycloak_issuer}/protocol/openid-connect/token"
    try:
        response = requests.post(
            token_url,
            data={
                "grant_type": "password",
                "client_id": settings.keycloak_audience,
                "username": username,
                "password": password,
            },
            timeout=settings.keycloak_connect_timeout,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Identity provider unreachable",
        ) from exc

    if response.status_code >= 400:
        # Never echo the provider's body verbatim: it can contain hints about
        # which factor failed. 401 for bad credentials, 502 otherwise.
        if response.status_code in (400, 401, 403):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Identity provider error",
        )

    token_payload = response.json()
    if "access_token" not in token_payload:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Identity provider error")
    return token_payload


@router.post("/login", response_model=Token)
async def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db=Depends(get_db),
):
    """Authenticate the user and return an access token. Also sets the
    httpOnly session cookie so the browser client authenticates without
    touching the token in JavaScript."""
    settings = get_settings()

    if settings.auth_mode == AUTH_MODE_KEYCLOAK:
        try:
            token_payload = await _keycloak_password_grant(form_data.username, form_data.password)
        except HTTPException as exc:
            if exc.status_code == 401:
                await audit_service.record_audit_event(
                    "LOGIN_FAILED",
                    actor_id=form_data.username,
                    resource_type="AUTH",
                    decision="deny",
                    reason="Invalid credentials (keycloak)",
                    db=db,
                )
            raise
        await audit_service.record_audit_event(
            "LOGIN_SUCCEEDED",
            actor_id=form_data.username,
            resource_type="AUTH",
            reason="Keycloak password grant",
            db=db,
        )
        _set_session_cookie(response, token_payload["access_token"])
        return {
            "access_token": token_payload["access_token"],
            "token_type": "bearer",
        }

    # Local mode (development): users table + HS256 token.
    user = await db.fetchrow(
        "SELECT id, username, hashed_password, role FROM public.users WHERE username = $1 AND is_active = TRUE",
        form_data.username,
    )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not user:
        await audit_service.record_audit_event(
            "LOGIN_FAILED", actor_id=form_data.username, resource_type="AUTH",
            decision="deny", reason="Unknown user (local)", db=db,
        )
        raise credentials_exception

    user_id, username, hashed_pass, role = user
    if not auth.verify_password(form_data.password, hashed_pass):
        await audit_service.record_audit_event(
            "LOGIN_FAILED", actor_id=form_data.username, resource_type="AUTH",
            decision="deny", reason="Invalid credentials (local)", db=db,
        )
        raise credentials_exception

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": username, "role": role, "id": user_id}, expires_delta=access_token_expires
    )
    await audit_service.record_audit_event(
        "LOGIN_SUCCEEDED",
        actor={"id": str(user_id), "username": username, "role": role},
        resource_type="AUTH",
        db=db,
    )
    _set_session_cookie(response, access_token)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response, current_user: dict = Depends(auth.get_current_user)):
    """Clear the httpOnly session cookie."""
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"status": "logged_out"}
