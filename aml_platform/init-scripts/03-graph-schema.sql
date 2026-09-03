-- ==========================================
-- PHASE 3: GRAPH SCHEMA & SUPER-NODE EXCLUSION
-- ==========================================

-- Ensure graph extension and path are set
LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- Initialize Vertex (Node) and Edge classes explicitly
-- This ensures strict structural integrity for the graph.
SELECT create_vlabel('aml_network', 'Entity');
SELECT create_vlabel('aml_network', 'SuperNode'); -- For exclusion logic
SELECT create_elabel('aml_network', 'Transfer');

-- ==========================================
-- SUPER-NODE CONFIGURATION
-- ==========================================
-- We maintain a relational list of known heavy connectivity nodes
-- e.g., Binance Hot Wallet, SWIFT Omnibus Settlement Account.
CREATE TABLE IF NOT EXISTS super_nodes (
    node_id VARCHAR(255) PRIMARY KEY,
    infrastructure_type VARCHAR(100),
    description TEXT,
    date_added TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed some examples
INSERT INTO super_nodes (node_id, infrastructure_type, description) VALUES
('0xBinanceHotWalletX', 'CRYPTO_EXCHANGE', 'Primary exit node for Binance CEX'),
('CHASE_OMNIBUS_77', 'FIAT_CLEARING', 'JPMorgan omnibus clearing account')
ON CONFLICT DO NOTHING;
