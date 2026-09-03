from fastapi import FastAPI
from app.api.v1 import alerts, cases, graph, auth, admin, reports, strs
from contextlib import asynccontextmanager
from app.db.session import init_db_pool, close_db_pool
from app.services import flowable_client
from fastapi.middleware.cors import CORSMiddleware
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db_pool()
    # Deploy Flowable workflow automatically on startup (runs asynchronously so as to not block API start)
    asyncio.create_task(flowable_client.deploy_process())
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

@app.get("/health")
def health_check():
    return {"status": "healthy", "engine": "Apache AGE", "version": "2.0.0"}
