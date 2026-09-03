"""
Flowable REST client (TASK-007: configuration + timeouts).

URL, credentials and timeout come from Settings (environment-driven; no
credential literals). Every call is bounded by FLOWABLE_TIMEOUT; upstream
failures raise ExternalServiceError rather than leaking driver details.
"""

import logging
import os

import httpx

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError, ServiceUnavailableError

logger = logging.getLogger(__name__)


def _client() -> httpx.AsyncClient:
    settings = get_settings()
    return httpx.AsyncClient(timeout=settings.flowable_timeout)


def _auth():
    settings = get_settings()
    if not settings.flowable_user or not settings.flowable_password:
        raise ServiceUnavailableError(
            "Workflow engine credentials not configured (FLOWABLE_USER / FLOWABLE_PASSWORD)"
        )
    return (settings.flowable_user, settings.flowable_password)


async def deploy_process():
    """Deploy the case workflow BPMN at startup (best-effort, logged)."""
    settings = get_settings()
    bpmn_path = os.path.join(os.path.dirname(__file__), "..", "resources", "aml_case_workflow.bpmn20.xml")
    if not os.path.exists(bpmn_path):
        logger.error("BPMN file not found at %s", bpmn_path)
        return
    try:
        async with _client() as client:
            with open(bpmn_path, "rb") as f:
                files = {"file": ("aml_case_workflow.bpmn20.xml", f, "text/xml")}
                response = await client.post(
                    f"{settings.flowable_url}/repository/deployments",
                    auth=_auth(), files=files,
                )
            if response.status_code in (200, 201):
                logger.info("Flowable process deployed successfully.")
            else:
                logger.error("Failed to deploy Flowable process: %s", response.status_code)
    except Exception as e:
        logger.error("Error deploying Flowable process (Flowable might not be ready): %s", e)


async def start_case_process(case_id: str) -> str:
    settings = get_settings()
    url = f"{settings.flowable_url}/runtime/process-instances"
    payload = {
        "processDefinitionKey": "aml_case_workflow",
        "businessKey": str(case_id),
        "variables": [{"name": "caseId", "value": str(case_id)}],
    }
    try:
        async with _client() as client:
            response = await client.post(url, json=payload, auth=_auth())
            response.raise_for_status()
            return response.json().get("id")
    except httpx.HTTPError as exc:
        raise ExternalServiceError("Workflow engine failed to start the case process",
                                   details={"case_id": str(case_id)}) from exc


async def get_active_task(process_instance_id: str) -> dict | None:
    if not process_instance_id:
        return None
    settings = get_settings()
    try:
        async with _client() as client:
            response = await client.get(
                f"{settings.flowable_url}/runtime/tasks",
                params={"processInstanceId": str(process_instance_id)},
                auth=_auth(),
            )
            if response.status_code == 200:
                tasks = response.json().get("data", [])
                if tasks:
                    return tasks[0]
    except Exception as e:
        logger.error("Error fetching Flowable task: %s", e)
    return None


async def complete_task(task_id: str, variables: dict = None):
    settings = get_settings()
    payload = {"action": "complete"}
    if variables:
        payload["variables"] = [{"name": k, "value": v} for k, v in variables.items()]
    try:
        async with _client() as client:
            response = await client.post(
                f"{settings.flowable_url}/runtime/tasks/{task_id}",
                json=payload, auth=_auth(),
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ExternalServiceError("Workflow engine failed to complete the task",
                                   details={"task_id": str(task_id)}) from exc
