-- ==========================================
-- PHASE 5: ALERT SCHEMA V5 ENRICHMENT (additive)
-- ==========================================
-- Implements Phase 0.1 of Implementation_Plan/20260710_typology_gap_plan.md.
--
-- Adds v5 converged-model columns to the existing `alerts` table so each
-- rule-engine alert records its stable scenario code/category/rail. All
-- columns are NULLable so existing OFAC_MATCH / hand-written alerts keep
-- working unchanged (backward compatible). Idempotent (IF NOT EXISTS).
--
-- NOTE: `alerts` is created (in 01-init.sql) under the active search_path,
-- which these scripts set to ag_catalog first. We mirror that here so the
-- ALTER resolves to the same schema the table lives in.

LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- Stable v5 scenario identifier (e.g. 'SCN_CIRCULAR_01'). NULL for legacy alerts.
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS scenario_code VARCHAR(50);

-- v5 scenario_category enum (STRUCTURING|LAYERING|PLACEMENT|TRAVEL_RULE_BREACH|
-- BLOCKCHAIN_RISK|UNHOSTED_WALLET|VELOCITY|PEP_MONITORING|CIRCULAR_FLOW|RAPID_MOVEMENT).
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS scenario_category VARCHAR(50);

-- Rail the alert fired on (FIAT|STABLECOIN|BOTH).
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS rail VARCHAR(20);

-- v5 ml_typology label (STRUCTURING|LAYERING|CRYPTO_MIXING|DEFI_LAUNDERING|SANCTIONS_EVASION).
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS ml_typology VARCHAR(50);

-- Detection window bounds (for time-windowed batch scenarios).
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS window_start TIMESTAMP WITH TIME ZONE;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS window_end TIMESTAMP WITH TIME ZONE;

-- Registry version that produced this alert (scenarios.RULE_VERSION) for audit/drift tracking.
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS rule_version VARCHAR(30);

-- Lookup indexes for the analyst queue (filter by scenario / category / status).
CREATE INDEX IF NOT EXISTS idx_alerts_scenario_code ON alerts(scenario_code);
CREATE INDEX IF NOT EXISTS idx_alerts_category ON alerts(scenario_category);
CREATE INDEX IF NOT EXISTS idx_alerts_rail ON alerts(rail);
CREATE INDEX IF NOT EXISTS idx_alerts_status_created ON alerts(status, created_at);

COMMENT ON COLUMN alerts.scenario_code IS 'Stable v5 scenario code (nullable for legacy OFAC_MATCH alerts).';
COMMENT ON COLUMN alerts.rule_version IS 'scenarios.RULE_VERSION when the alert was raised.';

-- ==========================================
-- FUTURE (not in this increment — documented as blocked in the plan):
-- The v5 spec's behavioural-baseline scenarios (Velocity, Dormant, Profile
-- Mismatch, Structuring-by-window) require tables that do not yet exist:
--   customer_behaviour_baseline, wallet_behaviour_baseline, party (with
--   expected_txn_profile), account (with account_status). Those tables and
--   the party/UBO graph dimension (needed for SCN_CROSS_RAIL_LAYER_01) are
--   prerequisites for Phases 1.2, 2 and 3 and are tracked in the plan.
-- ==========================================
