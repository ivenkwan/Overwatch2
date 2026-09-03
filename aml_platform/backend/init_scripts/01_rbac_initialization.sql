-- 01_rbac_initialization.sql

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. Create limited roles
DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'aml_api_role') THEN
      CREATE ROLE aml_api_role WITH LOGIN PASSWORD 'aml_secure_api_password' NOBYPASSRLS;
   END IF;
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'aml_etl_role') THEN
      CREATE ROLE aml_etl_role WITH LOGIN PASSWORD 'aml_secure_etl_password' BYPASSRLS;
   END IF;
END
$$;

GRANT ALL PRIVILEGES ON DATABASE age_prod_01 TO aml_api_role;
GRANT ALL PRIVILEGES ON DATABASE age_prod_01 TO aml_etl_role;

-- 2. Create Schema
CREATE SCHEMA IF NOT EXISTS app;

GRANT ALL ON SCHEMA app TO aml_api_role;
GRANT ALL ON SCHEMA app TO aml_etl_role;

-- 3. Core Tables
CREATE TABLE IF NOT EXISTS app.tenants (
  tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_code TEXT NOT NULL UNIQUE,
  tenant_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','suspended')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.app_users (
  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  keycloak_user_id UUID NOT NULL UNIQUE,
  username TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL UNIQUE,
  full_name TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled','locked')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.tenant_memberships (
  tenant_id UUID NOT NULL REFERENCES app.tenants(tenant_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES app.app_users(user_id) ON DELETE CASCADE,
  membership_status TEXT NOT NULL DEFAULT 'active' CHECK (membership_status IN ('active','invited','suspended')),
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, user_id)
);

CREATE TABLE IF NOT EXISTS app.roles (
  role_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  role_code TEXT NOT NULL UNIQUE,
  role_name TEXT NOT NULL,
  role_scope TEXT NOT NULL CHECK (role_scope IN ('realm','tenant','case')),
  description TEXT
);

CREATE TABLE IF NOT EXISTS app.permissions (
  permission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  permission_code TEXT NOT NULL UNIQUE,
  resource_type TEXT NOT NULL,
  action TEXT NOT NULL,
  description TEXT
);

CREATE TABLE IF NOT EXISTS app.role_permissions (
  role_id UUID NOT NULL REFERENCES app.roles(role_id) ON DELETE CASCADE,
  permission_id UUID NOT NULL REFERENCES app.permissions(permission_id) ON DELETE CASCADE,
  PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS app.user_tenant_roles (
  tenant_id UUID NOT NULL REFERENCES app.tenants(tenant_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES app.app_users(user_id) ON DELETE CASCADE,
  role_id UUID NOT NULL REFERENCES app.roles(role_id) ON DELETE CASCADE,
  granted_by UUID REFERENCES app.app_users(user_id),
  granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, user_id, role_id)
);

CREATE TABLE IF NOT EXISTS app.alerts (
  alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES app.tenants(tenant_id) ON DELETE CASCADE,
  alert_type TEXT NOT NULL,
  risk_score NUMERIC(10,2),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','triaged','escalated','closed')),
  customer_id TEXT,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by UUID REFERENCES app.app_users(user_id)
);

CREATE TABLE IF NOT EXISTS app.cases (
  case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES app.tenants(tenant_id) ON DELETE CASCADE,
  case_number TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL CHECK (status IN ('open','under_review','approved','filed','closed')),
  severity TEXT NOT NULL CHECK (severity IN ('low','medium','high','critical')),
  source_alert_id UUID REFERENCES app.alerts(alert_id),
  workflow_instance_id TEXT,
  created_by UUID NOT NULL REFERENCES app.app_users(user_id),
  assigned_to UUID REFERENCES app.app_users(user_id),
  reviewer_id UUID REFERENCES app.app_users(user_id),
  approver_id UUID REFERENCES app.app_users(user_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.case_acl (
  case_id UUID NOT NULL REFERENCES app.cases(case_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES app.app_users(user_id) ON DELETE CASCADE,
  access_level TEXT NOT NULL CHECK (access_level IN ('view','edit','review','approve')),
  granted_by UUID REFERENCES app.app_users(user_id),
  granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (case_id, user_id, access_level)
);

CREATE TABLE IF NOT EXISTS app.audit_access_events (
  event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES app.tenants(tenant_id),
  user_id UUID REFERENCES app.app_users(user_id),
  resource_type TEXT NOT NULL,
  resource_id UUID,
  action TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('allow','deny')),
  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  previous_hash TEXT,
  record_hash TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_tenant_created ON app.audit_access_events (tenant_id, created_at);

-- Grant privileges on all these tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app TO aml_api_role;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app TO aml_etl_role;
GRANT USAGE ON SCHEMA app TO aml_api_role;
GRANT USAGE ON SCHEMA app TO aml_etl_role;

-- Grant public schema access so flowable can initialize
GRANT ALL ON SCHEMA public TO aml_api_role;
GRANT ALL ON SCHEMA public TO aml_etl_role;

-- 4. Enable RLS
ALTER TABLE app.alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.cases ENABLE ROW LEVEL SECURITY;

-- Note: RLS policies require the transaction to set app.current_tenant
CREATE POLICY tenant_isolation_cases ON app.cases
    USING (tenant_id::text = current_setting('app.current_tenant', true));

CREATE POLICY tenant_isolation_alerts ON app.alerts
    USING (tenant_id::text = current_setting('app.current_tenant', true));
