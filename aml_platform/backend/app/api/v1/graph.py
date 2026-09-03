from fastapi import APIRouter, HTTPException, Depends, Query
from app.services import graph_service, pii_service
from app.core import auth
from app.db.session import get_db
import asyncpg

router = APIRouter()

@router.get("/network")
async def get_network(
    limit: int = 150,
    current_user: dict = Depends(auth.get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """
    Returns generic network topology using Apache AGE for the Unified Workspace.
    """
    try:
        subgraph = await graph_service.get_full_network(db, limit)
        # return subgraph unmasked for the demo
        return {"status": "success", "elements": pii_service.mask_pii(subgraph, "ADMIN")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/explore/{entity_id}")
async def explore_graph(
    entity_id: str,
    depth: int = Query(1, ge=1, le=5),
    current_user: dict = Depends(auth.get_current_user_with_scope("SENIOR_INVESTIGATOR")),
    db: asyncpg.Connection = Depends(get_db)
):
    """
    Explore the Apache AGE graph around a target entity.
    """
    try:
        subgraph = await graph_service.get_neighborhood(db, entity_id, depth)
        await auth.log_unmasking_event(current_user["id"], "GRAPH_EXPLORE", entity_id)
        return {"status": "success", "elements": pii_service.mask_pii(subgraph, current_user["role"])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
