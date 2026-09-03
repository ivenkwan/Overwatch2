"""
Test bootstrap: provide required environment variables BEFORE any app import.

The application fails fast without secrets (TASK-001), so tests supply
throwaway values: a random JWT secret generated per run and a placeholder
DSN that is never connected to.
"""

import os
import secrets

os.environ.setdefault("AUTH_MODE", "local")
os.environ.setdefault("JWT_SECRET_KEY", secrets.token_hex(32))
os.environ.setdefault(
    "DATABASE_URL", "postgresql://test_user:placeholder@localhost:5432/test_db"
)

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def _fresh_settings(monkeypatch):
    """Each test starts from the conftest baseline; restores env after."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
