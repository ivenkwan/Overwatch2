-- etl/sql/init_schema.sql

-- 1. Create AGE Extension
CREATE EXTENSION IF NOT EXISTS age;
LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- 2. Setup Relational Schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS core;

-- 3. Raw Table (For dead letters / debugging)
CREATE TABLE IF NOT EXISTS raw.wallet_ledger_dlq (
    id SERIAL PRIMARY KEY,
    source_filename VARCHAR(255),
    raw_payload JSONB,
    error_reason TEXT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Core Tables
CREATE TABLE IF NOT EXISTS core.customers (
    customer_num VARCHAR(255) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS core.counterparties (
    counterparty_id VARCHAR(255) PRIMARY KEY,
    counterparty_name VARCHAR(255),
    is_merchant BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS core.transactions (
    txn_hash VARCHAR(64) PRIMARY KEY,
    customer_num VARCHAR(255) REFERENCES core.customers(customer_num),
    counterparty_id VARCHAR(255) REFERENCES core.counterparties(counterparty_id),
    txn_date TIMESTAMP,
    txn_ref_no VARCHAR(255),
    txn_country VARCHAR(10),
    txn_currency VARCHAR(10),
    txn_currency_amount DECIMAL,
    txn_amount_in_hkd DECIMAL,
    cdi_code VARCHAR(2),
    txn_type VARCHAR(50),
    source_filename VARCHAR(255),
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Initialize the Apache AGE Graph
-- Note: docker-entrypoint-initdb.d only runs upon the very first volume creation
SELECT create_graph('tap_and_go_network');

-- Create node labels
SELECT create_vlabel('tap_and_go_network', 'Customer');
SELECT create_vlabel('tap_and_go_network', 'Counterparty');
SELECT create_vlabel('tap_and_go_network', 'Merchant');

-- Create edge labels
SELECT create_elabel('tap_and_go_network', 'TRANSFERRED');
SELECT create_elabel('tap_and_go_network', 'PAID');
