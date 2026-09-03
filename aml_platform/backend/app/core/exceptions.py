"""
Application exception hierarchy and the standard error envelope (TASK-009).

Every error returned by the API uses one JSON shape:

    {"error": {"code": "<machine-readable>", "message": "<human summary>",
               "details": {...optional...}}}

Handlers are registered in app.main. Internal exception details (driver
messages, stack traces) are logged server-side and never leaked to clients.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger("aml_errors")


class AMLBaseError(Exception):
    """Base class for all application errors."""

    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_payload(self) -> dict:
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}


class NotFoundError(AMLBaseError):
    status_code = 404
    code = "not_found"


class ValidationAppError(AMLBaseError):
    status_code = 400
    code = "validation_error"


class AuthorizationAppError(AMLBaseError):
    status_code = 403
    code = "forbidden"


class ConflictError(AMLBaseError):
    status_code = 409
    code = "conflict"


class ExternalServiceError(AMLBaseError):
    """An upstream dependency (Keycloak, Flowable, didvc-edge) failed."""

    status_code = 502
    code = "external_service_error"


class ServiceUnavailableError(AMLBaseError):
    status_code = 503
    code = "service_unavailable"


class DatabaseError(AMLBaseError):
    status_code = 500
    code = "database_error"


def database_error(operation: str, exc: Exception) -> DatabaseError:
    """Wrap an unexpected driver error without leaking internals."""
    logger.exception("Database failure during %s", operation)
    return DatabaseError("The request could not be completed due to a data store issue",
                         details={"operation": operation})
