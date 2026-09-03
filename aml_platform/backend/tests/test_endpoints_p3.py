"""P3 endpoint coverage: screening + audit + kpi-history routers via
TestClient with faked DB access (raises router-level coverage)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import AUTH_MODE_LOCAL, get_settings
from app.db.session import get_db


class EndpointFakeConn:
    """Fakes the fetch/fetchrow surface the routers use."""

    def __init__(self, rows=None):
        self.rows = rows or []
        self.statements = []

    async def fetch(self, sql, *args):
        self.statements.append((sql, args))
        if "ofac_blocklist" in sql and "wallet" in sql:
            return [{"wallet_address": "0xSanctioned1", "list_name": "ofac_wallet",
                     "record_id": "W1"}]
        if "wallet_address" in sql:  # internal blocklist
            return []
        return self.rows

    async def fetchrow(self, sql, *args):
        self.statements.append((sql, args))
        if "WITH ordered" in sql:  # audit chain verification
            return {"total": 0, "broken": 0, "broken_at": None}
        return None

    async def execute(self, sql, *args):
        self.statements.append((sql, args))
        return 1


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", AUTH_MODE_LOCAL)
    monkeypatch.setenv("JWT_SECRET_KEY", "s" * 48)
    get_settings.cache_clear()

    from app.main import app

    async def override_get_db():
        yield EndpointFakeConn()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def _token(role="SENIOR_INVESTIGATOR"):
    from app.core import auth
    from datetime import timedelta

    return auth.create_access_token(
        {"sub": "analyst", "role": role, "id": str(uuid.uuid4())},
        expires_delta=timedelta(minutes=5),
    )


def test_screening_screen_blocks_wallet(client):
    token = _token()
    resp = client.post(
        "/api/v1/screening/screen",
        json={"wallet_address": "0xSanctioned1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["disposition"] == "BLOCK"
    assert any(h["list"] == "ofac_wallet" for h in body["hits"])


def test_screening_requires_subject(client):
    token = _token()
    resp = client.post(
        "/api/v1/screening/screen", json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "validation_error"


def test_audit_export_requires_admin(client):
    token = _token("SENIOR_INVESTIGATOR")  # not ADMIN
    resp = client.get("/api/v1/audit/export", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_audit_export_returns_ndjson(client):
    from datetime import datetime, timezone

    fake = EndpointFakeConn(rows=[{
        "event_id": uuid.uuid4(), "tenant_id": None, "user_id": uuid.uuid4(),
        "resource_type": "ALERT", "resource_id": None, "action": "ALERT_ASSIGNED",
        "decision": "allow", "reason": None,
        "created_at": datetime.now(timezone.utc),
        "previous_hash": "genesis", "record_hash": "abc",
    }])

    from app.main import app

    async def override_get_db():
        yield fake

    app.dependency_overrides[get_db] = override_get_db
    token = _token("ADMIN")
    resp = client.get("/api/v1/audit/export", headers={"Authorization": f"Bearer {token}"})
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert '"action": "ALERT_ASSIGNED"' in resp.text


def test_audit_verify_admin(client):
    token = _token("ADMIN")
    resp = client.get("/api/v1/audit/verify", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["valid"] is True  # fake conn returns no rows
