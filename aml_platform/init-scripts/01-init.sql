-- Install and load Apache AGE extension
CREATE EXTENSION IF NOT EXISTS age;
LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- Initialize the Core Graph Namespace (ag_catalog) using AGE's dedicated function
SELECT create_graph('aml_network');

-- ==========================================
-- PHASE 1: RELATIONAL DDL (STAGING)
-- ==========================================

-- Fiat Staging Table
CREATE TABLE IF NOT EXISTS staging_fiat_raw (
    transfer_id VARCHAR(255) PRIMARY KEY,
    sender_account VARCHAR(255) NOT NULL,
    sender_bank_routing VARCHAR(255),
    receiver_account VARCHAR(255) NOT NULL,
    receiver_bank_routing VARCHAR(255),
    amount_usd NUMERIC(15, 2) NOT NULL,
    transaction_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING'
);

-- Crypto Staging Table
CREATE TABLE IF NOT EXISTS staging_crypto_raw (
    tx_hash VARCHAR(255) PRIMARY KEY,
    sender_wallet VARCHAR(255) NOT NULL,
    receiver_wallet VARCHAR(255) NOT NULL,
    asset_id VARCHAR(50) NOT NULL,
    volume_native NUMERIC(25, 8) NOT NULL,
    volume_usd NUMERIC(15, 2) NOT NULL,
    network VARCHAR(50) NOT NULL, -- e.g., ETHEREUM, BITCOIN
    transaction_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING'
);

-- ==========================================
-- PHASE 1: RELATIONAL DDL (REGULATORY)
-- ==========================================

-- OFAC Sanctions Blocklist
CREATE TABLE IF NOT EXISTS ofac_blocklist (
    entity_id VARCHAR(255) PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL, -- 'INDIVIDUAL', 'ORGANIZATION', 'WALLET'
    entity_name VARCHAR(500),
    wallet_address VARCHAR(255) UNIQUE,
    program VARCHAR(100),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- FATF Travel Rule Restrictions
CREATE TABLE IF NOT EXISTS fatf_rules (
    rule_id SERIAL PRIMARY KEY,
    sending_jurisdiction VARCHAR(50),
    receiving_jurisdiction VARCHAR(50),
    min_threshold_usd NUMERIC(15, 2) NOT NULL,
    required_info JSONB,
    active BOOLEAN DEFAULT TRUE
);

-- ==========================================
-- PHASE 1: RELATIONAL DDL (UI / INTEGRATION)
-- ==========================================

-- Alerts Table (Sinks from OFAC and Rule Engine)
CREATE TABLE IF NOT EXISTS alerts (
    alert_id SERIAL PRIMARY KEY,
    alert_type VARCHAR(100) NOT NULL, -- e.g., 'OFAC_MATCH', 'CIRCULAR_FLOW', 'SMURFING'
    severity VARCHAR(50) DEFAULT 'HIGH',
    trigger_entity VARCHAR(255) NOT NULL, -- Wallet or Account ID
    related_transactions JSONB, -- Array of tx hashes or fiat transfer IDs
    status VARCHAR(50) DEFAULT 'OPEN', -- OPEN, INVESTIGATING, CLOSED, FALSE_POSITIVE
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Dead Letter Queue (Unprocessable rows)
CREATE TABLE IF NOT EXISTS dead_letter_queue (
    error_id SERIAL PRIMARY KEY,
    source_table VARCHAR(100) NOT NULL,
    raw_payload JSONB NOT NULL,
    error_message TEXT NOT NULL,
    inserted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
