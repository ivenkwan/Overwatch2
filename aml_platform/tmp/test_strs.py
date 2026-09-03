# aml_platform/tmp/test_strs.py

import pytest
import sys
import os
from unittest.mock import AsyncMock
from uuid import uuid4

# Mock the app structure for testing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db

# Mock DB Connection
class MockConnection:
    def __init__(self):
        self.fetchrow = AsyncMock()
        self.fetch = AsyncMock()
        self.fetchval = AsyncMock()
        self.execute = AsyncMock()

@pytest.fixture
def mock_db():
    return MockConnection()

@pytest.fixture
def client(mock_db):
    async def override_get_db():
        yield mock_db
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_create_str_draft(client, mock_db):
    # Mock user and tenant resolution
    mock_db.fetchrow.side_effect = [
        {"user_id": uuid4()} # resolved user_id
    ]
    mock_db.fetchval.side_effect = [
        uuid4() # resolved tenant_id
    ]
    
    # Mock the insert result
    str_id = uuid4()
    tenant_id = uuid4()
    case_id = uuid4()
    mock_db.fetchrow.side_effect = [
        {"user_id": uuid4()},
        {
            "str_id": str_id,
            "tenant_id": tenant_id,
            "case_id": case_id,
            "status": "draft",
            "triggering_factors": "Triggered circular flow",
            "subject_background": "CDD notes",
            "digital_footprints": "IP: 1.2.3.4",
            "transaction_summary": "$1M total",
            "created_by": uuid4(),
            "created_at": "2026-07-02T12:00:00",
            "submitted_by": None,
            "submitted_at": None
        }
    ]

    payload = {
        "case_id": str(case_id),
        "triggering_factors": "Triggered circular flow",
        "subject_background": "CDD notes",
        "digital_footprints": "IP: 1.2.3.4",
        "transaction_summary": "$1M total"
    }

    response = client.post("/api/v1/str/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "draft"
    assert data["str_id"] == str(str_id)
    assert data["triggering_factors"] == "Triggered circular flow"

def test_list_strs(client, mock_db):
    # Mock user and tenant resolution
    mock_db.fetchrow.side_effect = [
        {"user_id": uuid4()}
    ]
    mock_db.fetchval.side_effect = [
        uuid4()
    ]

    str_id = uuid4()
    mock_db.fetch.return_value = [
        {
            "str_id": str_id,
            "tenant_id": uuid4(),
            "case_id": uuid4(),
            "status": "draft",
            "triggering_factors": "Factors...",
            "subject_background": "Background...",
            "digital_footprints": "Footprints...",
            "transaction_summary": "Summary...",
            "created_by": uuid4(),
            "created_at": "2026-07-02T12:00:00",
            "submitted_by": None,
            "submitted_at": None
        }
    ]

    response = client.get("/api/v1/str/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["str_id"] == str(str_id)

def test_get_str_detail(client, mock_db):
    mock_db.fetchrow.side_effect = [
        {"user_id": uuid4()}
    ]
    mock_db.fetchval.side_effect = [
        uuid4()
    ]

    str_id = uuid4()
    mock_db.fetchrow.side_effect = [
        {"user_id": uuid4()},
        {
            "str_id": str_id,
            "tenant_id": uuid4(),
            "case_id": uuid4(),
            "status": "draft",
            "triggering_factors": "Factors...",
            "subject_background": "Background...",
            "digital_footprints": "Footprints...",
            "transaction_summary": "Summary...",
            "created_by": uuid4(),
            "created_at": "2026-07-02T12:00:00",
            "submitted_by": None,
            "submitted_at": None
        }
    ]

    response = client.get(f"/api/v1/str/{str_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["str_id"] == str(str_id)

def test_update_str_draft(client, mock_db):
    mock_db.fetchrow.side_effect = [
        {"user_id": uuid4()}
    ]
    mock_db.fetchval.side_effect = [
        uuid4()
    ]

    str_id = uuid4()
    # Mock fetchval for status check, then fetchrow for update
    mock_db.fetchval.side_effect = [
        uuid4(), # tenant_id
        "draft"  # status
    ]
    mock_db.fetchrow.side_effect = [
        {"user_id": uuid4()},
        {
            "str_id": str_id,
            "tenant_id": uuid4(),
            "case_id": uuid4(),
            "status": "draft",
            "triggering_factors": "Updated Factors",
            "subject_background": "CDD notes",
            "digital_footprints": "IP: 1.2.3.4",
            "transaction_summary": "$1M total",
            "created_by": uuid4(),
            "created_at": "2026-07-02T12:00:00",
            "submitted_by": None,
            "submitted_at": None
        }
    ]

    payload = {
        "triggering_factors": "Updated Factors"
    }

    response = client.put(f"/api/v1/str/{str_id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["triggering_factors"] == "Updated Factors"

def test_update_filed_str_fails(client, mock_db):
    mock_db.fetchrow.side_effect = [
        {"user_id": uuid4()}
    ]
    mock_db.fetchval.side_effect = [
        uuid4()
    ]

    str_id = uuid4()
    mock_db.fetchval.side_effect = [
        uuid4(), # tenant_id
        "filed"  # status - ALREADY FILED
    ]

    payload = {
        "triggering_factors": "Cannot update this"
    }

    response = client.put(f"/api/v1/str/{str_id}", json=payload)
    assert response.status_code == 400
    assert "Cannot modify a finalized and filed STR" in response.json()["detail"]

def test_submit_str(client, mock_db):
    mock_db.fetchrow.side_effect = [
        {"user_id": uuid4()}
    ]
    mock_db.fetchval.side_effect = [
        uuid4()
    ]

    str_id = uuid4()
    mock_db.fetchval.side_effect = [
        uuid4(), # tenant_id
        "draft"  # current status
    ]
    mock_db.fetchrow.side_effect = [
        {"user_id": uuid4()},
        {
            "str_id": str_id,
            "tenant_id": uuid4(),
            "case_id": uuid4(),
            "status": "filed",
            "triggering_factors": "Factors...",
            "subject_background": "Background...",
            "digital_footprints": "Footprints...",
            "transaction_summary": "Summary...",
            "created_by": uuid4(),
            "created_at": "2026-07-02T12:00:00",
            "submitted_by": uuid4(),
            "submitted_at": "2026-07-02T13:00:00"
        }
    ]

    response = client.post(f"/api/v1/str/{str_id}/submit")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "filed"
    assert data["submitted_by"] is not None
