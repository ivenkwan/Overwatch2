-- ==========================================
-- PHASE 2: REGULATORY GATE PROCEDURES
-- ==========================================
-- This procedure screens the raw staging tables against the OFAC blocklist.
-- Any exact matches immediately sink a high-priority event to the alerts table.

CREATE OR REPLACE PROCEDURE sp_screen_ofac()
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Screen Fiat Staging (Accounts matching Entity ID)
    -- If either the sender or receiver is on the OFAC blocklist, insert an alert.
    INSERT INTO ag_catalog.alerts (alert_type, severity, trigger_entity, related_transactions, status)
    SELECT 
        'OFAC_MATCH_FIAT' AS alert_type,
        'CRITICAL' AS severity,
        -- Identify offending entity
        CASE WHEN o_sender.entity_id IS NOT NULL THEN f.sender_account ELSE f.receiver_account END AS trigger_entity,
        jsonb_build_array(f.transfer_id) AS related_transactions,
        'OPEN' AS status
    FROM ag_catalog.staging_fiat_raw f
    LEFT JOIN ag_catalog.ofac_blocklist o_sender ON f.sender_account = o_sender.entity_id
    LEFT JOIN ag_catalog.ofac_blocklist o_receiver ON f.receiver_account = o_receiver.entity_id
    WHERE f.status = 'PENDING'
      AND (o_sender.entity_id IS NOT NULL OR o_receiver.entity_id IS NOT NULL);

    -- 2. Screen Crypto Staging (Wallets matching Wallet Address)
    INSERT INTO ag_catalog.alerts (alert_type, severity, trigger_entity, related_transactions, status)
    SELECT 
        'OFAC_MATCH_CRYPTO' AS alert_type,
        'CRITICAL' AS severity,
        CASE WHEN o_sender.wallet_address IS NOT NULL THEN c.sender_wallet ELSE c.receiver_wallet END AS trigger_entity,
        jsonb_build_array(c.tx_hash) AS related_transactions,
        'OPEN' AS status
    FROM ag_catalog.staging_crypto_raw c
    LEFT JOIN ag_catalog.ofac_blocklist o_sender ON c.sender_wallet = o_sender.wallet_address
    LEFT JOIN ag_catalog.ofac_blocklist o_receiver ON c.receiver_wallet = o_receiver.wallet_address
    WHERE c.status = 'PENDING'
      AND (o_sender.wallet_address IS NOT NULL OR o_receiver.wallet_address IS NOT NULL);

    -- 3. Transition State
    -- Promote pending transactions to 'SCREENED' so they can be picked up by the Graph loader
    UPDATE ag_catalog.staging_fiat_raw SET status = 'SCREENED' WHERE status = 'PENDING';
    UPDATE ag_catalog.staging_crypto_raw SET status = 'SCREENED' WHERE status = 'PENDING';

END;
$$;
