-- aml_platform/backend/init_scripts/04_str_schema.sql

CREATE TABLE IF NOT EXISTS app.strs (
  str_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES app.tenants(tenant_id) ON DELETE CASCADE,
  case_id UUID REFERENCES app.cases(case_id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK (status IN ('draft', 'filed')) DEFAULT 'draft',
  triggering_factors TEXT,
  subject_background TEXT,
  digital_footprints TEXT,
  transaction_summary TEXT,
  created_by UUID REFERENCES app.app_users(user_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  submitted_by UUID REFERENCES app.app_users(user_id),
  submitted_at TIMESTAMPTZ
);

-- Enable RLS
ALTER TABLE app.strs ENABLE ROW LEVEL SECURITY;

-- Create Tenant Isolation Policy
CREATE POLICY tenant_isolation_strs ON app.strs
    USING (tenant_id::text = current_setting('app.current_tenant', true));

-- Grant privileges
GRANT ALL PRIVILEGES ON TABLE app.strs TO aml_api_role;
GRANT ALL PRIVILEGES ON TABLE app.strs TO aml_etl_role;
