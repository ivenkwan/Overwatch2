-- ==========================================
-- PHASE 6: PARTY / UBO DIMENSION (unblocks SCN_CROSS_RAIL_LAYER_01)
-- ==========================================
-- Implements the 1.2 prerequisite from
-- Implementation_Plan/20260710_typology_gap_plan.md §5.2.
--
-- The aml_network graph models instruments (fiat accounts, crypto wallets) as
-- Entity nodes with only {id, system}. To detect Cross-Rail Layering
-- ("stablecoin inflow -> fiat outflow within 48h, SAME beneficial owner") we
-- need a party dimension that links each instrument to the natural/legal
-- person controlling it, and a UBO chain that rolls legal entities up to
-- their ultimate beneficial owners. This script adds that relational
-- dimension and the graph labels the projection (etl/party_loader.py) writes.
--
-- Convention: relational tables are created under the active search_path
-- (ag_catalog first), matching how 01-init.sql created staging_*/alerts.

LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- party: the natural person or legal entity behind one or more instruments.
CREATE TABLE IF NOT EXISTS party (
    party_id VARCHAR(255) PRIMARY KEY,
    party_type VARCHAR(20) NOT NULL CHECK (party_type IN ('NATURAL', 'LEGAL')),
    display_name VARCHAR(500),
    kyc_status VARCHAR(20),                       -- PENDING | VERIFIED | ENHANCED
    risk_rating VARCHAR(20),                      -- LOW | MEDIUM | HIGH
    jurisdiction VARCHAR(50),
    expected_txn_profile JSONB,                   -- Phase 2 scenarios (Profile Mismatch) read this
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Links each graph Entity (fiat account id / wallet id) to its controlling party.
-- Maintained by KYC/onboarding; party_loader.py projects the current rows into
-- the graph. Many-to-one by default; ownership_pct supports shared accounts.
CREATE TABLE IF NOT EXISTS party_instrument (
    instrument_id VARCHAR(255) NOT NULL,          -- matches Entity.id
    instrument_type VARCHAR(20) NOT NULL CHECK (instrument_type IN ('FIAT_ACCOUNT', 'CRYPTO_WALLET')),
    party_id VARCHAR(255) NOT NULL REFERENCES party(party_id),
    ownership_pct NUMERIC(5,2) DEFAULT 100.00,
    valid_from TIMESTAMP WITH TIME ZONE,
    valid_to TIMESTAMP WITH TIME ZONE,            -- NULL = currently effective
    PRIMARY KEY (instrument_id, party_id)
);

-- UBO chain: natural persons who ultimately own/control a legal-entity party.
-- Self-referential on party; party_loader projects the edges so Cypher can
-- traverse party -> ... -> ubo with variable-length paths.
CREATE TABLE IF NOT EXISTS party_ubo (
    subject_party_id VARCHAR(255) NOT NULL REFERENCES party(party_id),  -- legal entity
    ubo_party_id     VARCHAR(255) NOT NULL REFERENCES party(party_id),  -- natural-person UBO
    ownership_pct NUMERIC(5,2),
    control_role VARCHAR(50),                     -- DIRECTOR | SHAREHOLDER | BENEFICIARY
    PRIMARY KEY (subject_party_id, ubo_party_id),
    CHECK (subject_party_id <> ubo_party_id)
);

CREATE INDEX IF NOT EXISTS idx_party_instrument_party ON party_instrument(party_id);
CREATE INDEX IF NOT EXISTS idx_party_instrument_eff ON party_instrument(instrument_id) WHERE valid_to IS NULL;
CREATE INDEX IF NOT EXISTS idx_party_ubo_ubo ON party_ubo(ubo_party_id);

-- ==========================================
-- GRAPH LABELS for the party dimension (written into aml_network by party_loader.py)
-- ==========================================
SELECT create_vlabel('aml_network', 'Party');
SELECT create_elabel('aml_network', 'OWNED_BY');   -- Entity -> Party
SELECT create_elabel('aml_network', 'UBO_OF');     -- Party  -> Party (legal entity -> natural-person UBO)

-- ==========================================
-- Seed: one UBO controlling both a fiat account and a crypto wallet via a
-- legal entity, demonstrating the cross-rail-same-UBO shape the rule targets.
-- Instrument ids below are EXAMPLES — map them to real Entity.id values from
-- your staging data (or the run_batch.py demo ids) to observe a live alert.
-- ==========================================
INSERT INTO party (party_id, party_type, display_name, risk_rating, jurisdiction) VALUES
  ('P_NAT_UBO_01', 'NATURAL', 'Ultimate Beneficial Owner (seed)', 'HIGH', 'HK'),
  ('P_LEG_SHELL_01', 'LEGAL', 'Shell Holding Ltd (seed)', 'MEDIUM', 'BVI')
ON CONFLICT (party_id) DO NOTHING;

INSERT INTO party_ubo (subject_party_id, ubo_party_id, ownership_pct, control_role) VALUES
  ('P_LEG_SHELL_01', 'P_NAT_UBO_01', 100.00, 'BENEFICIARY')
ON CONFLICT DO NOTHING;

-- EXAMPLE instrument mapping (uncomment & adjust ids to match your data):
-- INSERT INTO party_instrument (instrument_id, instrument_type, party_id) VALUES
--   ('ACC_SUSPECT_01', 'FIAT_ACCOUNT', 'P_LEG_SHELL_01'),
--   ('USER_A',         'CRYPTO_WALLET', 'P_LEG_SHELL_01')
-- ON CONFLICT DO NOTHING;
