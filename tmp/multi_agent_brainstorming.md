# Multi-Agent Brainstorming: Case Management via Flowable

## Phase 1: Single-Agent Design (Primary Designer)
**Goal:** Implement the Case Management module using a dockerized Flowable workflow engine.
**Initial Concept:**
1. Add `flowable-rest` Docker container alongside the backend.
2. The FastAPI backend sends HTTP requests to Flowable to deploy a Maker-Checker BPMN.
3. When a case is escalated from an alert, FastAPI starts a Flowable process.
4. `CaseManagement.tsx` fetches tasks from FastAPI, which proxies to Flowable's `/runtime/tasks` API.
5. Users interact to complete tasks ("Approve", "Reject").

## Phase 2: Structured Review Loop

### 1. Skeptic / Challenger
**Objection 1 (Identity Conflict):** Flowable has its own IDM. Overwatch uses Keycloak (FastAPI). If FastAPI just proxies tasks, how does Flowable know who the assignee is? Assigning tasks to specific Overwatch users in Flowable will fail if the users don't exist in Flowable's IDM.
**Objection 2 (Data Duplication):** Keeping case data in Flowable variables vs. `app.cases` in PostgreSQL will lead to synchronization bugs. If Flowable crashes, data is lost.

### 2. Constraint Guardian
**Objection 3 (Performance & Reliability):** Polling Flowable for every UI render of `CaseManagement.tsx` is inefficient. Overwatch needs strict timeouts. Flowable REST calls from FastAPI add latency.

### 3. User Advocate
**Objection 4 (UX Context Switching):** If the Maker-Checker workflow fails in Flowable, the user should not see raw external engine errors. The UI must cleanly show: "Pending Maker Action", "Pending Checker Approval" irrespective of Flowable's internal task IDs.

## Phase 3: Integration & Arbitration (Integrator)
**Resolutions:**
1. *Accept Objection 1:* We will NOT sync Keycloak users to Flowable. Instead, FastAPI will act as an administrative superuser to Flowable. Task assignment will be handled at the *group* level in Flowable (e.g., `role:INVESTIGATOR`), and FastAPI will enforce Keycloak RBAC before making the REST call to Flowable to claim/complete the task.
2. *Accept Objection 2:* Flowable will ONLY store state (BPMN process instance state and task state). All business data (customer ID, transactions, rationale) remains in `app.cases` in PostgreSQL. `app.cases` gets a new column: `workflow_instance_id`.
3. *Accept Objection 3:* FastAPI will query `app.cases` for the list of cases, and asynchronously fetch the active Flowable task for the detail view, rather than asking Flowable for the list of all cases.

---

## Decision Log

| Decision | Alternatives Considered | Objections Raised | Resolution / Rationale |
| :--- | :--- | :--- | :--- |
| **Identity Delegation** | Syncing Keycloak users into Flowable IDM using a nightly script or event listener. | Complex. Breaks if sync fails. | **FastAPI acts as a generic client.** Flowable tasks are assigned to application roles. FastAPI checks Keycloak token first, then completes the task on Flowable using a system account. |
| **Data Storage Truth** | Storing form data/notes as Flowable process variables. | Duplication, risky sync issues, hard to query in graphs. | **Dual-State.** Business data stays in PostgreSQL (`app.cases`). Flowable only knows the `businessKey` (the Case ID) and handles state transitions. |
| **BPMN Deployment** | Using Flowable Modeler UI. | Hard to automate in CI/CD. | **Auto-Deploy via FastAPI.** On startup, FastAPI reads a `case_lifecycle.bpmn20.xml` file and deploys it via REST if it doesn't exist. |

## Final Disposition
**APPROVED**. The design is robust, prevents identity mismatches, respects the single-source-of-truth for business data, and orchestrates the maker-checker flow correctly.
