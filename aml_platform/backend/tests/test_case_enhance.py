"""TASK-015/017: case-enhance endpoints (validation + SQL shapes)."""

import asyncio
import uuid

import pytest

from app.api.v1.case_enhance import (
    add_case_note,
    bulk_case_action,
    record_workflow_event,
)
from app.core.exceptions import ValidationAppError


def run(coro):
    return asyncio.run(coro)


class NotesFakeConn:
    def __init__(self):
        self.statements = []

    async def fetchrow(self, sql, *args):
        self.statements.append((sql, args))
        if "app_users" in sql:
            return {"user_id": uuid.uuid4()}
        if "INSERT INTO app.case_notes" in sql:
            return {"note_id": uuid.uuid4(), "created_at": "now"}
        return None

    async def fetch(self, sql, *args):
        self.statements.append((sql, args))
        return []

    async def execute(self, sql, *args):
        self.statements.append((sql, args))
        return 1  # one row affected per UPDATE


def _user(role="ADMIN"):
    return {"id": str(uuid.uuid4()), "username": "u", "role": role}


def test_add_note_requires_body():
    conn = NotesFakeConn()
    with pytest.raises(ValidationAppError):
        run(add_case_note("case-1", {"body": "x"}, current_user=_user(), db=conn))
    assert conn.statements == []


def test_add_note_inserts_and_returns_id():
    conn = NotesFakeConn()
    result = run(add_case_note("case-1", {"body": "reviewed on 2026-09-03"},
                               current_user=_user(), db=conn))
    assert result["status"] == "success" and result["note_id"]
    insert = [s for s in conn.statements if "INSERT INTO app.case_notes" in s[0]]
    assert insert and len(insert[0][1]) == 5


def test_bulk_validates_inputs():
    """Role enforcement lives in the FastAPI dependency (require_role) —
    covered at the route level elsewhere; here we exercise the function's
    own validation."""
    conn = NotesFakeConn()
    head = {"id": str(uuid.uuid4()), "username": "h", "role": "DEPARTMENT_HEAD"}
    with pytest.raises(ValidationAppError):
        run(bulk_case_action({"case_ids": [], "status": "closed"},
                             current_user=head, db=conn))
    with pytest.raises(ValidationAppError):
        run(bulk_case_action({"case_ids": ["c1"], "status": "bogus"},
                             current_user=head, db=conn))
    with pytest.raises(ValidationAppError):
        run(bulk_case_action({"case_ids": list(range(300)), "status": "closed"},
                             current_user=head, db=conn))


def test_bulk_updates_return_counts():
    conn = NotesFakeConn()
    head = {"id": str(uuid.uuid4()), "username": "h", "role": "DEPARTMENT_HEAD"}
    result = run(bulk_case_action({"case_ids": ["c1", "c2", "c3"], "status": "closed"},
                                  current_user=head, db=conn))
    assert result == {"status": "success", "updated": 3, "target": 3}
    updates = [s for s in conn.statements if "UPDATE app.cases SET status" in s[0]]
    assert len(updates) == 3


def test_workflow_event_recorded_with_static_sql():
    conn = NotesFakeConn()
    run(record_workflow_event(conn, "case-1", "wf-9", "checkerTask", "task_completed",
                              {"action": "approve", "new_status": "approved"}))
    insert = [s for s in conn.statements if "INSERT INTO app.workflow_event" in s[0]]
    assert insert
    sql, args = insert[0]
    assert "$5::jsonb" in sql
    assert args[4]  # serialized detail json


def test_notes_and_timeline_sql_static():
    import pathlib
    source = pathlib.Path(
        "/home/ivenkwan/repo/Overwatch2/aml_platform/backend/app/api/v1/case_enhance.py"
    ).read_text()
    # no SQL is assembled dynamically (no f-string/triple-f-string literals)
    for bad in ("f\"\"\"", "f'''", "SELECT " + "{", "sql = f"):
        assert bad not in source
    assert "app.case_notes" in source and "app.workflow_event" in source
