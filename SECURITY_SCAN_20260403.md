# Security Scan Report
**Date:** 2026-04-03
**Scope:** `z:\GITHUB\Overwatch` codebase
**Framework:** `SECURITY.md` (ISO 27001, PCI-DSS v4.0.1, OWASP LLM 2025)

## Executive Summary
A static scan of the codebase has been conducted against the rules defined in `SECURITY.md`. Several critical violations regarding hardcoded credentials and dependency management require remediation.

## Identified Issues

### 1. Hardcoded Secrets and Credentials
**Violation of SECURITY.md Section 2.1 (Secrets and Credentials)**
Multiple files contain hardcoded secrets or credentials, violating the rule that all secrets must be stored in an approved secrets manager:

* **JWT Secret Key:**
  * `aml_platform/backend/app/core/auth.py`: `SECRET_KEY = "aml_super_secret_key_change_me"`
* **Database Credentials & Seed Passwords:**
  * `aml_platform/docker-compose.yml` (lines 10, 33): Hardcoded `POSTGRES_PASSWORD: secure_password_123` and `DATABASE_URL`.
  * `aml_platform/backend/app/db/session.py` (line 11): Hardcoded `password="secure_password_123"`.
  * `aml_platform/api/server.py` (line 24): Hardcoded `password="secure_password_123"`.
  * `aml_platform/init-scripts/04-users-and-workflow.sql` (lines 19-24): Hardcoded plaintext password used for hashing seed users (`password123`).
* **ETL Scripts with Hardcoded Passwords:**
  * `aml_platform/etl/run_demo_demo.py` (line 15)
  * `aml_platform/etl/run_batch.py` (line 20)
  * `aml_platform/etl/rule_engine.py` (line 21)
  * `aml_platform/etl/graph_loader.py` (line 17)

### 2. Dependency Version Pinning
**Violation of SECURITY.md Section 4 (Dependency Security)**
The policy explicitly states that all packages in `requirements.txt` and equivalent files must have an explicit version pin (e.g., `pkg==1.2.3`), and wildcards are prohibited.

* **Python Dependencies:** Let `aml_platform/requirements.txt` contains completely unpinned packages (e.g., `fastapi`, `uvicorn`, `psycopg2-binary`, `pydantic`).
* **Node Dependencies:** The `aml_platform/frontend/package.json` relies on caret (`^`) versioning (e.g., `"@tanstack/react-query": "^5.96.2"`, `"tailwindcss": "^4"`) instead of exact version locks.

### 3. Agentic AI & Sensitive Data (PCI-DSS)
* No unmasked PAN/CVV exposures or hardcoded AI Agent identity tokens/OpenAI keys were found in the current static scan.
* System components currently invoke minimal or structural AI workflows; ensure any future integrations dynamically fetch temporary authentication tokens and enforce output filtering.
