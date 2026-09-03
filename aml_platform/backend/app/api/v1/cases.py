from fastapi import APIRouter, Depends, HTTPException
import asyncpg
from typing import List, Dict, Any
from app.db.session import get_db
from app.core import auth
from app.services import flowable_client

router = APIRouter()

@router.get("/")
async def get_cases(
    current_user: dict = Depends(auth.get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    query = """
        SELECT case_id, case_number, status, severity, created_by, assigned_to, reviewer_id, approver_id, created_at, workflow_instance_id
        FROM app.cases
        ORDER BY created_at DESC
        LIMIT 100
    """
    rows = await db.fetch(query)
    cases = []
    for row in rows:
        case = dict(row)
        if case.get("case_id"):
            case["case_id"] = str(case["case_id"])
        cases.append(case)
        
    return cases

@router.post("/")
async def create_case(
    payload: dict,
    current_user: dict = Depends(auth.get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    alert_id = payload.get("alert_id")
    # For now, generate a random tenant manually as we don't handle cross-schema perfectly here, 
    # but normally rely on `current_setting('app.current_tenant')` configured in RLS.
    # Simplified creation logic:
    query = """
        INSERT INTO app.cases (tenant_id, case_number, status, severity, created_by, source_alert_id)
        VALUES ((SELECT tenant_id FROM app.tenants LIMIT 1), 'CASE-' || floor(random() * 1000000)::text, 'open', 'medium', (SELECT user_id FROM app.app_users LIMIT 1), $1)
        RETURNING case_id
    """
    try:
        row = await db.fetchrow(query, alert_id if alert_id else None)
        case_id = str(row["case_id"])
        
        # Start the flowable process
        instance_id = await flowable_client.start_case_process(case_id)
        
        # Update case with workflow instance ID
        update_query = "UPDATE app.cases SET workflow_instance_id = $1 WHERE case_id = $2"
        await db.execute(update_query, instance_id, row["case_id"])
        
        return {"status": "success", "case_id": case_id, "workflow_instance_id": instance_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{case_id}")
async def get_case_detail(
    case_id: str,
    current_user: dict = Depends(auth.get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    query = """
        SELECT case_id, case_number, status, severity, created_by, assigned_to, reviewer_id, approver_id, created_at, workflow_instance_id
        FROM app.cases
        WHERE case_id = $1
    """
    row = await db.fetchrow(query, case_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
        
    case_info = dict(row)
    case_info["case_id"] = str(case_info["case_id"])
    
    # Query Flowable for active task
    active_task = None
    if case_info.get("workflow_instance_id"):
        task = await flowable_client.get_active_task(case_info["workflow_instance_id"])
        if task:
            active_task = {
                "id": task.get("id"),
                "name": task.get("name"),
                "assignee": task.get("assignee"),
                "taskDefinitionKey": task.get("taskDefinitionKey")
            }
            
    case_info["activeTask"] = active_task
    
    return case_info

@router.post("/{case_id}/action")
async def action_case(
    case_id: str,
    payload: dict,
    current_user: dict = Depends(auth.get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    action_type = payload.get("action")
    notes = payload.get("notes", "")
    
    query = "SELECT workflow_instance_id FROM app.cases WHERE case_id = $1"
    row = await db.fetchrow(query, case_id)
    if not row or not row["workflow_instance_id"]:
        raise HTTPException(status_code=400, detail="Case lacks an active workflow instance")
        
    instance_id = row["workflow_instance_id"]
    active_task = await flowable_client.get_active_task(instance_id)
    
    if not active_task:
        raise HTTPException(status_code=400, detail="No active task found for this case")
        
    task_key = active_task.get("taskDefinitionKey")
    
    flowable_vars = {}
    new_db_status = None
    
    if task_key == "makerTask" and action_type == "submit":
        # Role check should go here
        new_db_status = "under_review"
        
    elif task_key == "checkerTask":
        if action_type == "approve":
            flowable_vars["approved"] = True
            new_db_status = "approved"
        elif action_type == "reject":
            flowable_vars["approved"] = False
            new_db_status = "open"
        else:
            raise HTTPException(status_code=400, detail="Invalid action for checkerTask")
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action {action_type} for task {task_key}")
        
    # Complete the Flowable Task
    await flowable_client.complete_task(active_task["id"], variables=flowable_vars)
    
    # Update PostgreSQL State
    if new_db_status:
        update_query = "UPDATE app.cases SET status = $1 WHERE case_id = $2"
        await db.execute(update_query, new_db_status, case_id)
        
    return {"status": "success", "new_status": new_db_status}
