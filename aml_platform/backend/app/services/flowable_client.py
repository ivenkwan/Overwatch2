import httpx
import os
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Default out of the box authentication for flowable-rest
FLOWABLE_URL = os.getenv("FLOWABLE_REST_URL", "http://aml-flowable:8080/flowable-rest/service")
FLOWABLE_USER = os.getenv("FLOWABLE_USER", "rest-admin")
FLOWABLE_PASS = os.getenv("FLOWABLE_PASSWORD", "test")

def get_auth():
    return (FLOWABLE_USER, FLOWABLE_PASS)

async def deploy_process():
    bpmn_path = os.path.join(os.path.dirname(__file__), "..", "resources", "aml_case_workflow.bpmn20.xml")
    if not os.path.exists(bpmn_path):
        logger.error(f"BPMN file not found at {bpmn_path}")
        return

    url = f"{FLOWABLE_URL}/repository/deployments"
    async with httpx.AsyncClient() as client:
        try:
            with open(bpmn_path, "rb") as f:
                files = {'file': ('aml_case_workflow.bpmn20.xml', f, 'text/xml')}
                response = await client.post(url, auth=get_auth(), files=files)
                if response.status_code in [200, 201]:
                    logger.info("Flowable process deployed successfully.")
                else:
                    logger.error(f"Failed to deploy Flowable process: {response.text}")
        except Exception as e:
            logger.error(f"Error deploying Flowable process (Flowable might not be ready): {e}")

async def start_case_process(case_id: str) -> str:
    url = f"{FLOWABLE_URL}/runtime/process-instances"
    payload = {
        "processDefinitionKey": "aml_case_workflow",
        "businessKey": str(case_id),
        "variables": [
            {"name": "caseId", "value": str(case_id)}
        ]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, auth=get_auth())
        response.raise_for_status()
        data = response.json()
        return data.get("id")

async def get_active_task(process_instance_id: str) -> dict:
    if not process_instance_id:
        return None
    url = f"{FLOWABLE_URL}/runtime/tasks"
    params = {"processInstanceId": str(process_instance_id)}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, auth=get_auth())
            if response.status_code == 200:
                data = response.json()
                tasks = data.get("data", [])
                if tasks:
                    return tasks[0] # Return the most recent active task
        except Exception as e:
            logger.error(f"Error fetching Flowable task: {e}")
    return None

async def complete_task(task_id: str, variables: dict = None):
    url = f"{FLOWABLE_URL}/runtime/tasks/{task_id}"
    payload = {"action": "complete"}
    if variables:
        payload["variables"] = [{"name": k, "value": v} for k, v in variables.items()]
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, auth=get_auth())
        response.raise_for_status()
