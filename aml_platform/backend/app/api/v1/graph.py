from fastapi import APIRouter, Depends, Query
from app.services import graph_service, pii_service, audit_service
from app.core import auth
from app.core.exceptions import ValidationAppError, database_error
from app.db.session import get_db
import asyncpg

router = APIRouter()

@router.get("/network")
async def get_network(
    limit: int = Query(150, ge=1, le=500),
    current_user: dict = Depends(auth.get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """
    Returns generic network topology using Apache AGE for the Unified Workspace.
    """
    try:
        subgraph = await graph_service.get_full_network(db, limit)
        return {"status": "success", "elements": pii_service.mask_pii(subgraph, current_user["role"])}
    except graph_service.InvalidGraphInput as e:
        raise ValidationAppError(str(e))
    except Exception as e:
        raise database_error("graph.network", e)

@router.get("/explore/{entity_id}")
async def explore_graph(
    entity_id: str,
    depth: int = Query(1, ge=1, le=graph_service.MAX_DEPTH),
    current_user: dict = Depends(auth.get_current_user_with_scope("SENIOR_INVESTIGATOR")),
    db: asyncpg.Connection = Depends(get_db)
):
    """
    Explore the Apache AGE graph around a target entity.
    """
    try:
        subgraph = await graph_service.get_neighborhood(db, entity_id, depth)
        await audit_service.log_unmasking_event(current_user, "GRAPH_EXPLORE", entity_id, db=db)
        return {"status": "success", "elements": pii_service.mask_pii(subgraph, current_user["role"])}
    except graph_service.InvalidGraphInput as e:
        raise ValidationAppError(str(e))
    except Exception as e:
        raise database_error("graph.explore", e)
