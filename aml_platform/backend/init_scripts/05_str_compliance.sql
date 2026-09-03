-- 05_str_compliance.sql (TASK-006)
-- STR regulatory compliance: richer filing-status lifecycle, append-only
-- version history with automatic snapshotting on every update.

-- 1. Extend the status lifecycle: draft -> under_review -> filed, plus withdrawn.
ALTER TABLE app.strs DROP CONSTRAINT IF EXISTS strs_status_check;
ALTER TABLE app.strs ADD CONSTRAINT strs_status_check
    CHECK (status IN ('draft', 'under_review', 'filed', 'withdrawn'));

-- 2. Version history (append-only; every UPDATE snapshots the prior state).
CREATE TABLE IF NOT EXISTS app.str_versions (
  version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  str_id UUID NOT NULL REFERENCES app.strs(str_id) ON DELETE CASCADE,
  tenant_id UUID REFERENCES app.tenants(tenant_id),
  version_no INT NOT NULL,
  snapshot JSONB NOT NULL,
  changed_by UUID REFERENCES app.app_users(user_id),
  changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (str_id, version_no)
);

CREATE INDEX IF NOT EXISTS idx_str_versions_str ON app.str_versions(str_id, version_no DESC);

ALTER TABLE app.str_versions ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_str_versions ON app.str_versions
    USING (tenant_id::text = current_setting('app.current_tenant', true));

GRANT ALL PRIVILEGES ON TABLE app.str_versions TO aml_api_role;
GRANT ALL PRIVILEGES ON TABLE app.str_versions TO aml_etl_role;

-- 3. Snapshot trigger. The acting user is provided by the API via
--    set_config('app.actor_user_id', ...) on the same transaction.
CREATE OR REPLACE FUNCTION app.snapshot_str_version()
RETURNS TRIGGER AS $$
DECLARE
    next_no INT;
    actor TEXT;
BEGIN
    SELECT COALESCE(MAX(version_no), 0) + 1 INTO next_no
    FROM app.str_versions WHERE str_id = OLD.str_id;

    actor := current_setting('app.actor_user_id', true);

    INSERT INTO app.str_versions (str_id, tenant_id, version_no, snapshot, changed_by)
    VALUES (
        OLD.str_id,
        OLD.tenant_id,
        next_no,
        to_jsonb(OLD),
        CASE WHEN actor IS NULL OR actor = '' THEN NULL
             ELSE actor::uuid END
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_snapshot_str_version ON app.strs;
CREATE TRIGGER trg_snapshot_str_version
    BEFORE UPDATE ON app.strs
    FOR EACH ROW EXECUTE FUNCTION app.snapshot_str_version();
