-- ==========================================
-- PHASE 8: AUTHORIZATION-AWARE REGULATORY GATE (AWI TASK-049 / TASK-050)
-- ==========================================
-- 049 — Revoked-credential internal blocklist (Cap.656-style blacklisting):
--       wallets whose binding credential was REVOKED are blocked at the
--       pre-graph gate with a CRITICAL `CREDENTIAL_REVOKED` alert, and their
--       staging rows are marked BLOCKED so the graph promotion (which only
--       promotes SCREENED rows) never ingests them.
-- 050 — Authorization metadata attach: every staging row carries the wallet
--       authorization state (authorized flag + registry party) BEFORE the
--       OFAC screen runs. Screening ALWAYS runs for authorized wallets —
--       this procedure attaches metadata; it never skips the screen.
--
-- NOTE ON FEED SOURCE (cross-DB): the AWI credential lifecycle
-- (app.party_credential REVOKED / wallet deauthorization) is enforced by the
-- nightly T1_CREDENTIAL_STATUS batch against the compose database, which is
-- a SEPARATE database from this aml_network demo database. Until the two are
-- unified (TASK-060 v5 migration), operators feed this blocklist through
-- sp_internal_blocklist_add() (or an integration job) when a binding is
-- revoked; sp_internal_blocklist_remove() restores a re-verified wallet.

LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- 1. Internal blocklist of de-authorized wallets (revoked bindings).
CREATE TABLE IF NOT EXISTS ag_catalog.internal_wallet_blocklist (
    wallet_address        VARCHAR(255) PRIMARY KEY,
    reason                TEXT NOT NULL,
    source_credential_id  VARCHAR(255),
    added_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    added_by              VARCHAR(255),
    active                BOOLEAN NOT NULL DEFAULT TRUE
);

-- 2. Blocklist lifecycle (revoke -> re-verify -> restore).
CREATE OR REPLACE PROCEDURE sp_internal_blocklist_add(
    p_wallet_address TEXT, p_reason TEXT, p_source_credential_id TEXT DEFAULT NULL,
    p_added_by TEXT DEFAULT NULL
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO ag_catalog.internal_wallet_blocklist
        (wallet_address, reason, source_credential_id, added_by)
    VALUES (p_wallet_address, p_reason, p_source_credential_id, p_added_by)
    ON CONFLICT (wallet_address) DO UPDATE
        SET reason = p_reason,
            source_credential_id = COALESCE(p_source_credential_id,
                ag_catalog.internal_wallet_blocklist.source_credential_id),
            added_at = now(),
            active = TRUE;
END;
$$;

CREATE OR REPLACE PROCEDURE sp_internal_blocklist_remove(p_wallet_address TEXT)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE ag_catalog.internal_wallet_blocklist
    SET active = FALSE
    WHERE wallet_address = p_wallet_address;
END;
$$;

-- 3. Gate step: alert + BLOCK revoked wallets BEFORE the OFAC screen runs.
--    Matched PENDING rows are set to BLOCKED; sp_screen_ofac's
--    PENDING->SCREENED promotion therefore never touches them, so revoked
--    wallets cannot enter the graph. Authorized wallets are NOT exempted
--    here: they flow through to sp_screen_ofac like everyone else.
CREATE OR REPLACE PROCEDURE sp_screen_internal_blocklist()
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO ag_catalog.alerts (alert_type, severity, trigger_entity, related_transactions, status)
    SELECT DISTINCT ON (c.tx_hash)
        'CREDENTIAL_REVOKED' AS alert_type,
        'CRITICAL' AS severity,
        CASE WHEN b_sender.active AND c.sender_wallet = b_sender.wallet_address
             THEN c.sender_wallet ELSE c.receiver_wallet END AS trigger_entity,
        jsonb_build_array(c.tx_hash) AS related_transactions,
        'OPEN' AS status
    FROM ag_catalog.staging_crypto_raw c
    LEFT JOIN ag_catalog.internal_wallet_blocklist b_sender
           ON c.sender_wallet = b_sender.wallet_address AND b_sender.active
    LEFT JOIN ag_catalog.internal_wallet_blocklist b_receiver
           ON c.receiver_wallet = b_receiver.wallet_address AND b_receiver.active
    WHERE c.status = 'PENDING'
      AND (b_sender.wallet_address IS NOT NULL OR b_receiver.wallet_address IS NOT NULL)
    ORDER BY c.tx_hash;

    -- Quarantine: matched rows never reach the graph promotion.
    UPDATE ag_catalog.staging_crypto_raw c
    SET status = 'BLOCKED'
    FROM ag_catalog.internal_wallet_blocklist b
    WHERE c.status = 'PENDING'
      AND b.active
      AND (c.sender_wallet = b.wallet_address OR c.receiver_wallet = b.wallet_address);
END;
$$;

-- 4. Attach authorization metadata to staging rows (TASK-050). The registry
--    (compose DB app.wallet_authorization) is mirrored here by the
--    onboarding/ops flow; the attach is a LEFT JOIN so unauthorized or
--    unregistered wallets are still screened normally.
CREATE TABLE IF NOT EXISTS ag_catalog.wallet_authorization_mirror (
    wallet_address VARCHAR(255) PRIMARY KEY,
    authorized     BOOLEAN NOT NULL DEFAULT FALSE,
    party_id       VARCHAR(255),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE ag_catalog.staging_crypto_raw ADD COLUMN IF NOT EXISTS auth_metadata JSONB;
ALTER TABLE ag_catalog.staging_fiat_raw ADD COLUMN IF NOT EXISTS auth_metadata JSONB;

CREATE OR REPLACE PROCEDURE sp_attach_auth_metadata()
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE ag_catalog.staging_crypto_raw c
    SET auth_metadata = jsonb_build_object(
            'sender_authorized', wa_s.authorized,
            'receiver_authorized', wa_r.authorized
        )
    FROM ag_catalog.wallet_authorization_mirror wa_s
    LEFT JOIN ag_catalog.wallet_authorization_mirror wa_r
           ON wa_r.wallet_address = c.receiver_wallet
    WHERE c.sender_wallet = wa_s.wallet_address
      AND c.status IN ('PENDING', 'SCREENED');

    -- Attach both directions where only the receiver is registered.
    UPDATE ag_catalog.staging_crypto_raw c
    SET auth_metadata = jsonb_build_object(
            'sender_authorized', FALSE,
            'receiver_authorized', wa_r.authorized
        )
    FROM ag_catalog.wallet_authorization_mirror wa_r
    WHERE c.receiver_wallet = wa_r.wallet_address
      AND c.auth_metadata IS NULL
      AND c.status IN ('PENDING', 'SCREENED');
END;
$$;
