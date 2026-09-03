# Implementation Plan: Users, RBAC, & Case Management Workflow

Following the **Structured Multi-Agent Brainstorming** process, we have transformed the initial requirements into a robust, secure, and production-ready design.

## User Review Required

> [!IMPORTANT]
> **Workflow Enforcement**: The Maker/Checker system will strictly prevent the same user from both proposing and approving an alert closure, even if they have Senior credentials. Rejecting a proposed closure will require mandatory notes from the Checker.

---

## 🧠 Brainstorming Review Log

### 1️⃣ Primary Designer Proposal
- **Schema**: Introduce `users` table. Enhance existing `alerts` table with `status`, `assigned_to`, `maker_id`, `checker_id`, `maker_notes`, `checker_notes`.
- **Roles**: `JUNIOR_ANALYST`, `SENIOR_INVESTIGATOR`, `DEPARTMENT_HEAD`, `ADMIN`.
- **APIs**: Auth (Login), Admin (Create User), Case Actions (Assign, Propose, Approve, Reject), Reports (Monthly KPI).
- **Seeding**: SQL init script using `pgcrypto` to hash default user passwords.

### 2️⃣ Skeptic / Challenger
- **Objection**: How do reviewers find pending work? Live report aggregations might be slow.
- **Resolution (Accepted)**: Add specific query filters to the alerts API (e.g., `?status=PENDING_APPROVAL`). Add database indexes to `status` and `assigned_to` columns.

### 3️⃣ Constraint Guardian
- **Objection**: Maker and Checker identities must be mutually exclusive. An investigator should not approve their own work.
- **Resolution (Accepted)**: The API layer will enforce `current_user.id != alert.maker_id` during the `/approve` action.

### 4️⃣ User Advocate
- **Objection**: When a Checker rejects a proposed closure and sends it back to the Maker, the Maker needs to know why to fix it.
- **Resolution (Accepted)**: The `/reject` endpoint will enforce a mandatory `checker_notes` payload from the Senior reviewer.

---

## Proposed Changes

### 1. Database Schema Updates
#### [NEW] `init-scripts/04-users-and-workflow.sql`
- Enable `pgcrypto` extension for password hashing.
- Create `users` table with standard fields and role ENUM.
- Alter `ag_catalog.alerts` to add workflow columns (`status`, `assigned_to`, `maker_id`, `checker_id`, `resolution_notes`).
- Insert 4 default seeded users (one for each role).

### 2. Backend Domain Models & Auth
#### [NEW] `backend/app/schemas/user.py`
- Pydantic models for User creation, login, and token response.
#### [MODIFY] `backend/app/core/auth.py`
- Replace hardcoded mock tokens with real JWT generation and decoding using `PyJWT` and `passlib`.
- Update scope checking to validate database-backed roles.

### 3. Backend APIs & Services
#### [NEW] `backend/app/api/v1/auth.py`
- `POST /login`: Authenticate and return JWT.
#### [NEW] `backend/app/api/v1/admin.py`
- `POST /users`: Provision new users (Requires `ADMIN` role).
#### [NEW] `backend/app/api/v1/reports.py`
- `GET /monthly`: Aggregate maker/checker metrics and alert resolutions (Requires `DEPARTMENT_HEAD` role).
#### [MODIFY] `backend/app/api/v1/alerts.py`
- Add endpoints for the Maker/Checker workflow:
  - `POST /{id}/assign` (Sets `assigned_to`)
  - `POST /{id}/propose-close` (Maker: sets status to `PENDING_APPROVAL`)
  - `POST /{id}/approve` (Checker: sets status to `CLOSED`, enforces Maker != Checker)
  - `POST /{id}/reject` (Checker: sets status back to `OPEN`, requires notes)

### 4. Dependencies
#### [MODIFY] `backend/requirements.txt`
- Ensure `passlib[bcrypt]`, `PyJWT`, and `python-multipart` are included for auth.

## Verification Plan

### Automated/Manual Testing
1. **Provisioning**: Start DB, verify 4 default users exist. Use Admin user to create a new user.
2. **Authentication**: Login via `/api/v1/auth/login` to receive JWT.
3. **Workflow**: 
   - Assign alert as Junior.
   - Propose closure as Junior.
   - Attempt to approve as Junior (Should FAIL - 403 Forbidden).
   - Attempt to approve as Senior (Should PASS).
4. **Reporting**: Hit the `/monthly` endpoint as Department Head to verify aggregations.
