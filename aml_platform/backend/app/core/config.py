"""
Centralised security configuration.

All credentials and security-sensitive settings are read exclusively from
environment variables. No fallback literals exist anywhere in the codebase;
the application refuses to start when a required secret is missing or weak
(see validate_security_config, invoked at application startup).
"""

import os
import secrets
from functools import lru_cache

# Values that must never be accepted as secrets, regardless of source.
FORBIDDEN_SECRETS = {
    "aml_super_secret_key_change_me_dev",  # former in-code default (revoked)
    "changeme",
    "change_me",
    "change-me",
    "secret",
    "password",
    "admin",
}

MIN_SECRET_LENGTH = 32

AUTH_MODE_LOCAL = "local"
AUTH_MODE_KEYCLOAK = "keycloak"


class SecurityConfigError(RuntimeError):
    """Raised at startup when the security configuration is unusable."""


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is not None and value.strip() == "":
        return default
    return value if value is not None else default


def _validate_secret(name: str, value: str) -> None:
    normalized = value.strip().lower()
    if normalized in FORBIDDEN_SECRETS:
        raise SecurityConfigError(
            f"{name} is set to a known-weak/revoked value. Generate a fresh secret "
            f"(e.g. `openssl rand -hex 32`) and set it via the environment."
        )
    if len(value) < MIN_SECRET_LENGTH:
        raise SecurityConfigError(
            f"{name} must be at least {MIN_SECRET_LENGTH} characters. "
            f"Generate one with `openssl rand -hex 32`."
        )


class Settings:
    """Lazy application settings resolved from the environment."""

    def __init__(self) -> None:
        self.auth_mode = (_env("AUTH_MODE", AUTH_MODE_KEYCLOAK) or "").strip().lower()
        if self.auth_mode not in (AUTH_MODE_LOCAL, AUTH_MODE_KEYCLOAK):
            raise SecurityConfigError(
                f"AUTH_MODE must be '{AUTH_MODE_LOCAL}' or '{AUTH_MODE_KEYCLOAK}', got '{self.auth_mode}'"
            )

        self.jwt_secret_key = _env("JWT_SECRET_KEY")
        self.access_token_expire_minutes = int(_env("ACCESS_TOKEN_EXPIRE_MINUTES", "60") or "60")

        # Keycloak (used when auth_mode == keycloak)
        self.keycloak_url = (_env("KEYCLOAK_URL") or "").rstrip("/")
        self.keycloak_realm = _env("KEYCLOAK_REALM", "aml")
        self.keycloak_audience = _env("KEYCLOAK_AUDIENCE", "aml-portal")
        self.keycloak_leeway_seconds = int(_env("KEYCLOAK_LEEWAY_SECONDS", "30") or "30")
        self.keycloak_role_prefix = _env("KEYCLOAK_ROLE_PREFIX", "aml_")
        self.keycloak_connect_timeout = float(_env("KEYCLOAK_CONNECT_TIMEOUT", "5") or "5")

        # Keycloak admin client (user provisioning only); required lazily so the
        # API can run without admin credentials when provisioning is not used.
        self.keycloak_admin_user = _env("KEYCLOAK_ADMIN_USER")
        self.keycloak_admin_password = _env("KEYCLOAK_ADMIN_PASSWORD")
        self.keycloak_admin_realm = _env("KEYCLOAK_ADMIN_REALM", "master")

        # External services (TASK-007: URLs and timeouts are configuration).
        self.flowable_url = (_env("FLOWABLE_REST_URL",
                                  "http://aml-flowable:8080/flowable-rest/service") or "").rstrip("/")
        self.flowable_user = _env("FLOWABLE_USER")  # required when workflows are used
        self.flowable_password = _env("FLOWABLE_PASSWORD")
        self.flowable_timeout = float(_env("FLOWABLE_TIMEOUT", "10") or "10")

        # Query cache (TASK-011): in-memory TTL fallback; Redis-ready.
        self.cache_ttl_seconds = int(_env("CACHE_TTL_SECONDS", "15") or "15")

        # Database pool (TASK-008).
        self.db_pool_min = int(_env("DB_POOL_MIN", "2") or "2")
        self.db_pool_max = int(_env("DB_POOL_MAX", "20") or "20")
        self.db_query_timeout_ms = int(_env("DB_QUERY_TIMEOUT_MS", "30000") or "30000")
        self.db_acquire_timeout_s = float(_env("DB_ACQUIRE_TIMEOUT_S", "10") or "10")

        # didvc-edge M2M verification provider (AWI TASK-037). No defaults for
        # the URL/key: unset means the onboarding feature is disabled.
        self.identity_provider_url = _env("IDENTITY_PROVIDER_URL")
        self.identity_provider_api_key = _env("IDENTITY_PROVIDER_API_KEY")
        self.identity_provider_tenant = _env("IDENTITY_PROVIDER_TENANT", "aml")
        self.identity_provider_timeout = float(_env("IDENTITY_PROVIDER_TIMEOUT", "5") or "5")
        self.identity_provider_retries = int(_env("IDENTITY_PROVIDER_RETRIES", "2") or "2")

        # didvc platform (issuation) API for first-party wallet bindings (TASK-046).
        self.identity_platform_url = _env("IDENTITY_PLATFORM_URL")
        self.identity_platform_token = _env("IDENTITY_PLATFORM_TOKEN")

    @property
    def keycloak_issuer(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}"

    @property
    def keycloak_jwks_url(self) -> str:
        return f"{self.keycloak_issuer}/protocol/openid-connect/certs"

    def validate(self) -> None:
        """Fail fast on missing/weak configuration. Called at startup."""
        if self.auth_mode == AUTH_MODE_LOCAL:
            if not self.jwt_secret_key:
                raise SecurityConfigError(
                    "JWT_SECRET_KEY environment variable is required when AUTH_MODE=local. "
                    "Generate one with `openssl rand -hex 32`."
                )
            _validate_secret("JWT_SECRET_KEY", self.jwt_secret_key)
        else:
            if not self.keycloak_url:
                raise SecurityConfigError(
                    "KEYCLOAK_URL environment variable is required when AUTH_MODE=keycloak "
                    "(e.g. http://keycloak:8080)."
                )

        dsn = _env("DATABASE_URL")
        if dsn and "aml_secure_api_password" in dsn:
            raise SecurityConfigError(
                "DATABASE_URL still contains the revoked default password. "
                "Set a real credential via the environment."
            )

    def rotate_hint(self) -> str:
        return secrets.token_urlsafe(4)  # demo helper only; never printed with secrets


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.validate()
    return settings


def validate_security_config() -> Settings:
    """Startup entry point: build, validate and cache settings.

    Raises SecurityConfigError (RuntimeError) so the application fails to
    start when required secrets are missing, weak, or revoked.
    """
    return get_settings()
