# Walkthrough: User DB, RBAC, & Case Management

I have executed the implementation plan for the **User Database and Maker/Checker Workflow**. The AML platform is now equipped with persistent users, secure authentication, and a rigorous compliance-oriented case workflow.

## 🏗️ Architectural Enhancements

### 1. Database Schema (`04-users-and-workflow.sql`)
- Created the `public.users` table with baked-in ENUM roles (`JUNIOR_ANALYST`, `SENIOR_INVESTIGATOR`, `DEPARTMENT_HEAD`, `ADMIN`).
- Implemented **password hashing** at the database seed level using `pgcrypto` (bcrypt).
- Seeded the database with 4 default users (e.g., `junior_01`, `senior_01`) password: `password123`.
- Altered the `ag_catalog.alerts` table to track the workflow state: `status`, `assigned_to`, `maker_id`, `checker_id`, `resolution_notes`, and `checker_notes`.

### 2. Backend Authentication (`core/auth.py` & `api/v1/auth.py`)
- Replaced the hardcoded mock tokens with authentic **JWT (JSON Web Tokens)** logic.
- Integrated `passlib[bcrypt]` to securely verify hashed passwords against the database.
- Implemented `POST /api/v1/auth/login` for the frontend to acquire access tokens.

### 3. Case Management Workflow (`api/v1/alerts.py`)
The alerts API has been significantly upgraded to enforce a **Maker/Checker** lifecycle:
1. **Assign** (`POST /{id}/assign`): Claims an `OPEN` alert.
2. **Propose Close** (`POST /{id}/propose-close`): The "Maker" (Junior) proposes a resolution and provides notes.
3. **Approve** (`POST /{id}/approve`): The "Checker" (Senior) reviews and closes the alert. The API strictly **prevents the Maker from being the Checker**.
4. **Reject** (`POST /{id}/reject`): The Checker kicks the alert back, which mandates a `notes` payload to explain the rejection to the Maker.

### 4. Admin & Reporting (`api/v1/admin.py`, `api/v1/reports.py`)
- **Admin**: An exclusive endpoint for creating new user accounts securely.
- **Reporting**: Calculates real-time KPIs (e.g., alert status counts, total cases approved by each Senior Investigator) specifically scoped for the `DEPARTMENT_HEAD` dashboard.

## 🚀 Next Steps
The backend is now ready for these features. You can integrate these API routes into the Next.js `Dashboard`! For example, the `Department Head` can fetch the `/api/v1/reports/monthly` data to populate the KPI cards.
