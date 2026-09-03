"""TASK-004: audit persistence semantics (normalisation, fail-soft, export)."""

import asyncio
import json
import uuid

from app.services import audit_service
from app.services.audit_store import to_uuid


class FakeConn:
    def __init__(self, fail=False):
        self.statements = []
        self.fail = fail
        # pretend the actor has no app_users mapping
        self.results = {  # sql prefix -> row returned
            "SELECT user_id FROM app.app_users": None,
        }

    async def fetchrow(self, sql, *args):
        self.statements.append((sql, args))
        for prefix, row in self.results.items():
            if sql.strip().startswith(prefix):
                if row is None:
                    return None
                return {"user_id": row}
        if self.fail:
            raise RuntimeError("db down")
        if "RETURNING event_id" in sql:
            return {"event_id": uuid.uuid4()}
        return {"total": 0, "broken": 0, "broken_at": None}

    async def fetch(self, sql, *args):
        self.statements.append((sql, args))
        return []

    async def execute(self, sql, *args):
        self.statements.append((sql, args))


def run(coro):
    return asyncio.run(coro)


def test_record_inserts_with_normalised_params():
    conn = FakeConn()
    ok = run(audit_service.record_audit_event(
        "ALERT_ASSIGNED",
        actor={"id": "7", "username": "analyst_01", "role": "JUNIOR_ANALYST"},
        resource_type="ALERT",
        resource_id="TXN-123-abc",  # non-UUID -> travels in reason
        db=conn,
    ))
    assert ok is True
    insert = [s for s in conn.statements if "INSERT INTO app.audit_access_events" in s[0]]
    assert len(insert) == 1
    args = insert[0][1]
    assert args[2] == "ALERT"
    assert args[4] == "ALERT_ASSIGNED"
    assert args[5] == "allow"
    assert args[6] is None or "actor=analyst_01" in args[6]
    assert args[6] and "resource=TXN-123-abc" in args[6]  # string id preserved in reason
    assert args[3] is None  # resource_id column only takes UUIDs


def test_uuid_resource_id_uses_column():
    conn = FakeConn()
    rid = str(uuid.uuid4())
    run(audit_service.record_audit_event(
        "CASE_ACTION", actor={"id": "7", "username": "u"}, resource_type="CASE",
        resource_id=rid, db=conn,
    ))
    insert = [s for s in conn.statements if "INSERT INTO" in s[0]][0]
    assert insert[1][3] == uuid.UUID(rid)


def test_deny_decision_enforced():
    conn = FakeConn()
    run(audit_service.record_audit_event(
        "LOGIN_FAILED", actor_id="someone", resource_type="AUTH",
        decision="deny", db=conn,
    ))
    insert = [s for s in conn.statements if "INSERT INTO" in s[0]][0]
    assert insert[1][5] == "deny"


def test_db_failure_never_raises():
    conn = FakeConn(fail=True)
    ok = run(audit_service.record_audit_event(
        "LOGIN_SUCCEEDED", actor_id="someone", db=conn,
    ))
    assert ok is False  # mirrored to logger, request unaffected


def test_uuid_actor_id_populates_user_column():
    """A UUID actor id (Keycloak `sub`) is stored directly in the user_id column."""
    conn = FakeConn()
    sub = str(uuid.uuid4())
    run(audit_service.record_audit_event(
        "LOGIN_SUCCEEDED", actor_id=sub, db=conn,
    ))
    insert = [s for s in conn.statements if "INSERT INTO" in s[0]][0]
    assert insert[1][1] == uuid.UUID(sub)  # (tenant_id, user_id, ...)


def test_non_uuid_actor_leaves_user_column_null():
    conn = FakeConn()
    run(audit_service.record_audit_event(
        "LOGIN_SUCCEEDED", actor_id="7", db=conn,
    ))
    insert = [s for s in conn.statements if "INSERT INTO" in s[0]][0]
    assert insert[1][1] is None


def test_to_uuid():
    assert to_uuid(None) is None
    assert to_uuid("not-a-uuid") is None
    assert to_uuid(12345) is None
    assert to_uuid("11111111-1111-1111-1111-111111111111") == uuid.UUID(
        "11111111-1111-1111-1111-111111111111"
    )


def test_ndjson_export_is_valid_json_lines():
    now = "2026-09-03T00:00:00+00:00"
    events = [
        {
            "event_id": str(uuid.uuid4()),
            "created_at": now,
            "tenant_id": None,
            "user_id": str(uuid.uuid4()),
            "resource_type": "ALERT",
            "resource_id": None,
            "action": "ALERT_ASSIGNED",
            "decision": "allow",
            "reason": "actor=u1",
            "previous_hash": "genesis",
            "record_hash": "abc123",
        }
    ]
    output = audit_service.export_audit_events_ndjson(events)
    parsed = json.loads(output.splitlines()[0])
    assert parsed["action"] == "ALERT_ASSIGNED"
    assert parsed["record_hash"] == "abc123"
    assert parsed["timestamp"] == now
