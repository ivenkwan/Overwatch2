"""TASK-001: startup validation of security configuration (fail fast)."""

import pytest

from app.core.config import (
    AUTH_MODE_KEYCLOAK,
    AUTH_MODE_LOCAL,
    SecurityConfigError,
    Settings,
    get_settings,
    validate_security_config,
)

STRONG_SECRET = "a" * 48


def test_local_mode_requires_jwt_secret(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", AUTH_MODE_LOCAL)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    settings = Settings()
    with pytest.raises(SecurityConfigError):
        settings.validate()


def test_local_mode_rejects_revoked_default_secret(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", AUTH_MODE_LOCAL)
    monkeypatch.setenv("JWT_SECRET_KEY", "aml_super_secret_key_change_me_dev")
    settings = Settings()
    with pytest.raises(SecurityConfigError):
        settings.validate()


def test_local_mode_rejects_weak_short_secret(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", AUTH_MODE_LOCAL)
    monkeypatch.setenv("JWT_SECRET_KEY", "short")
    settings = Settings()
    with pytest.raises(SecurityConfigError):
        settings.validate()


def test_local_mode_accepts_strong_secret(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", AUTH_MODE_LOCAL)
    monkeypatch.setenv("JWT_SECRET_KEY", STRONG_SECRET)
    Settings().validate()


def test_keycloak_mode_requires_keycloak_url(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", AUTH_MODE_KEYCLOAK)
    monkeypatch.delenv("KEYCLOAK_URL", raising=False)
    settings = Settings()
    with pytest.raises(SecurityConfigError):
        settings.validate()


def test_keycloak_mode_with_url_is_valid(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", AUTH_MODE_KEYCLOAK)
    monkeypatch.setenv("KEYCLOAK_URL", "http://keycloak:8080")
    Settings().validate()


def test_revoked_db_password_in_dsn_is_rejected(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", AUTH_MODE_LOCAL)
    monkeypatch.setenv("JWT_SECRET_KEY", STRONG_SECRET)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://aml_api_role:aml_secure_api_password@localhost:5432/db",
    )
    settings = Settings()
    with pytest.raises(SecurityConfigError):
        settings.validate()


def test_invalid_auth_mode_rejected(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "none")
    with pytest.raises(SecurityConfigError):
        Settings()


def test_validate_security_config_caches(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", AUTH_MODE_LOCAL)
    monkeypatch.setenv("JWT_SECRET_KEY", STRONG_SECRET)
    get_settings.cache_clear()
    settings = validate_security_config()
    assert settings.auth_mode == AUTH_MODE_LOCAL
    assert settings.jwt_secret_key == STRONG_SECRET
