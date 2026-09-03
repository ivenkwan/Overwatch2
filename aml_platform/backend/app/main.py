from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api.v1 import alerts, cases, graph, auth, admin, reports, strs, audit, onboarding
from contextlib import asynccontextmanager
from app.core.config import get_settings, validate_security_config
from app.core.exceptions import AMLBaseError
from app.db.session import db_health, init_db_pool, close_db_pool
from app.logging_config import configure_logging
from app.services import flowable_client
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import os

logger = logging.getLogger("aml_main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: fail fast when required secrets/config are missing or weak (TASK-001)
    settings = validate_security_config()
    configure_logging(json_logs=os.getenv("JSON_LOGS", "1") not in ("0", "false", "no"))
    await init_db_pool()
    # Deploy Flowable workflow automatically on startup (runs asynchronously so as to not block API start)
    asyncio.create_task(flowable_client.deploy_process())
    logger.info("backend started (auth_mode=%s, pool=%s..%s)",
                settings.auth_mode, settings.db_pool_min, settings.db_pool_max)
    yield
    # Shutdown
    await close_db_pool()

app = FastAPI(
    title="Overwatch AML Platform",
    description="Unified TradFi and Web3 Fund Flow Analysis Engine",
    version="2.0.0",
    lifespan=lifespan
)

import os

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(cases.router, prefix="/api/v1/cases", tags=["Cases"])
app.include_router(graph.router, prefix="/api/v1/graph", tags=["Graph Explorer"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(strs.router, prefix="/api/v1/str", tags=["STR"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["Audit"])
app.include_router(onboarding.router, prefix="/api/v1/onboarding", tags=["Onboarding (Authorized Wallets)"])

@app.get("/health")
async def health_check():
    """Liveness/readiness probe: reports DB pool status (TASK-008)."""
    db = await db_health()
    overall = "healthy" if db.get("status") == "ok" else "degraded"
    return {"status": overall, "engine": "Apache AGE", "version": "2.0.0", "database": db}

# ----------------------------------------------------------------------
# Global error handlers (TASK-009): one JSON envelope for every failure.
# ----------------------------------------------------------------------
@app.exception_handler(AMLBaseError)
async def aml_error_handler(request: Request, exc: AMLBaseError):
    return JSONResponse(status_code=exc.status_code, content=exc.to_payload())


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": f"http_{exc.status_code}", "message": detail, "details": {}}},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {
            "code": "request_validation_error",
            "message": "Request parameters failed validation",
            "details": {"errors": [
                {"loc": [str(p) for p in e.get("loc", [])], "msg": e.get("msg")}
                for e in exc.errors()
            ]},
        }},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error",
                           "message": "An unexpected error occurred", "details": {}}},
    )
