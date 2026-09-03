#!/bin/bash
# 00-roles-from-env.sh — creates database roles with passwords sourced
# EXCLUSIVELY from environment variables (TASK-001: no credential literals
# in source). Runs once on first database initialisation, before
# 01_rbac_initialization.sql which grants privileges to these roles.
#
# Passwords must be alphanumeric (they are embedded into generated SQL);
# generate with: openssl rand -hex 32

set -e

: "${POSTGRES_USER:?POSTGRES_USER must be set}"
: "${AML_API_PASSWORD:?AML_API_PASSWORD must be set}"
: "${AML_ETL_PASSWORD:?AML_ETL_PASSWORD must be set}"
: "${KEYCLOAK_DB_PASSWORD:?KEYCLOAK_DB_PASSWORD must be set}"

psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres <<SQL
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'aml_api_role') THEN
      CREATE ROLE aml_api_role WITH LOGIN PASSWORD '${AML_API_PASSWORD}' NOBYPASSRLS;
   END IF;
   IF NOT EXISTS (pg_roles WHERE rolname = 'aml_etl_role') THEN
      CREATE ROLE aml_etl_role WITH LOGIN PASSWORD '${AML_ETL_PASSWORD}' BYPASSRLS;
   END IF;
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'keycloak') THEN
      CREATE ROLE keycloak LOGIN PASSWORD '${KEYCLOAK_DB_PASSWORD}';
   END IF;
END
\$\$;
SQL

if [ "$(psql -tAc "SELECT 1 FROM pg_database WHERE datname='keycloak'" -U "$POSTGRES_USER")" != "1" ]; then
    psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -c "CREATE DATABASE keycloak OWNER keycloak"
fi
