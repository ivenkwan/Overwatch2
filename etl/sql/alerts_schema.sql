-- etl/sql/alerts_schema.sql
-- Detection alert sink for the tap_and_go pipeline (age_prod_01).
-- Apply once alongside init_schema.sql (fresh volumes or existing).
-- Mirrors the v5 alert shape used by aml_platform's rule engine so the two
-- systems can later be unified without a schema migration.

LOAD 'age';
SET search_path = ag_catalog, "$user", public;

CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE IF NOT EXISTS core.alerts (
    alert_id             SERIAL PRIMARY KEY,
    scenario_code        VARCHAR(50) NOT NULL,   -- e.g. TG_SCN_STRUCT_01
    scenario_category    VARCHAR(50) NOT NULL,   -- STRUCTURING | CIRCULAR_FLOW | LAYERING ...
    rail                 VARCHAR(20),            -- FIAT (tap_and_go is a fiat retail rail)
    severity             VARCHAR(20) NOT NULL,   -- LOW | MEDIUM | HIGH | CRITICAL
    trigger_entity       VARCHAR(255) NOT NULL,  -- Customer.customer_num
    related_transactions JSONB,                  -- array of txn_hash
    rule_version         VARCHAR(30),            -- detection.RULE_VERSION for audit/drift
    status               VARCHAR(20) DEFAULT 'OPEN',  -- OPEN | INVESTIGATING | CLOSED | FALSE_POSITIVE
    created_at           TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at          TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_alerts_scenario ON core.alerts(scenario_code);
CREATE INDEX IF NOT EXISTS idx_alerts_status_created ON core.alerts(status, created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_entity ON core.alerts(trigger_entity);
