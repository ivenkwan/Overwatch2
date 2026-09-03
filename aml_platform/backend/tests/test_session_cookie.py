"""httpOnly cookie session: login sets it, protected routes accept it,
logout clears it (browser-session client support)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.core.config import AUTH_MODE_LOCAL, get_settings
from app.db.session import get_db


class LoginFakeConn:
    def __init__(self, user_row):
        self._user = user_row

    async def fetchrow(self, sql, *args):
        if "app.audit_access_events" in sql or "INSERT INTO" in sql:
            return None
        if "public.users" in sql:
            # the login route unpacks positionally (asyncpg Record semantics)
            return (self._user["id"], self._user["username"],
                    self._user["hashed_password"], self._user["role"])
        return self._user

    async def execute(self, sql, *args):
        return None

    async def fetch(self, sql, *args):
        return []


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", AUTH_MODE_LOCAL)
    monkeypatch.setenv("JWT_SECRET_KEY", "s" * 48)
    get_settings.cache_clear()
    auth._keycloak_validator = None

    from app.main import app

    hashed = auth.get_password_hash("correct-horse")
    user_row = {
        "id": str(uuid.uuid4()),
        "username": "analyst_01",
        "hashed_password": hashed,
        "role": "SENIOR_INVESTIGATOR",
    }

    async def override_get_db():
        yield LoginFakeConn(user_row)

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    get_settings.cache_clear()
    auth._keycloak_validator = None


def _login(client, username="analyst_01", password="correct-horse"):
    return client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )


def test_login_sets_http_only_session_cookie(client):
    response = _login(client)
    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "")
    assert "aml_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie.lower() or "samesite=lax" in set_cookie.lower()


def test_cookie_authenticates_protected_route(client):
    login = _login(client)
    cookie = {"aml_session": login.json()["access_token"]}
    # A protected endpoint called WITHOUT an Authorization header but WITH
    # the session cookie must succeed (the browser-session flow).
    response = client.get("/api/v1/alerts/feed", cookies=cookie)
    assert response.status_code == 200


def test_no_cookie_no_token_is_401(client):
    response = client.get("/api/v1/alerts/feed")
    assert response.status_code == 401


def test_logout_clears_cookie(client):
    login = _login(client)
    cookie = {"aml_session": login.json()["access_token"]}
    response = client.post("/api/v1/auth/logout", cookies=cookie)
    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "")
    assert "aml_session=" in set_cookie and "Max-Age=0" in set_cookie
