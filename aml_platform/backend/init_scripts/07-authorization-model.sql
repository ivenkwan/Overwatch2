-- 07-authorization-model.sql (AWI TASK-036, Phase 1)
-- Authorized-wallet data model per ADR-0002 / feasability.md §6.1.
--
-- Self-sufficient for the deployed stack (age_prod_01): brings the party /
-- UBO dimension into the `app` schema (the legacy aml_network copy lives in
-- aml_platform/init-scripts/06-party-ubo-model.sql under ag_catalog) and
-- adds the credential + wallet-authorization tables on top.
--
--  * app.party / party_instrument / party_ubo — the identity dimension
--    (previously designed in 06-*; now instantiated for this database).
--  * app.party_credential — every verified credential with an evidence hash
--    (verification-response digest) so decisions stay reconstructible.
--  * app.wallet_authorization — the denormalized "authorized wallet"
--    registry consumed by the screening gate and risk scoring; the
--    plaintext address lives only here (a PII-masked field at the API).
--  * app.credential_check_dlq — dead-letter queue for the nightly
--    T1_CREDENTIAL_STATUS re-verification batch (TASK-048).
--  * v5 converged-model alignment: columns map onto aml_core.account
--    (blockchain_address, wallet_custody_type), account_party_link and
--    party_wallet at migration time (TASK-060 keeps the mapping doc).

CREATE SCHEMA IF NOT EXISTS app;

-- 1. Party / UBO dimension (identity behind instruments)
CREATE TABLE IF NOT EXISTS app.party (
    party_id            VARCHAR(255) PRIMARY KEY,
    party_type          VARCHAR(20) NOT NULL CHECK (party_type IN ('NATURAL', 'LEGAL')),
    display_name        VARCHAR(500),
    kyc_status          VARCHAR(20) CHECK (kyc_status IN ('PENDING', 'VERIFIED', 'ENHANCED')),
    risk_rating         VARCHAR(20) CHECK (risk_rating IN ('LOW', 'MEDIUM', 'HIGH')),
    jurisdiction        VARCHAR(50),
    did                 VARCHAR(255),
    onboarding_channel  VARCHAR(30) CHECK (onboarding_channel IN ('VC_ISSUER', 'iAM_SMART', 'MANUAL')),
    expected_txn_profile JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.party_instrument (
    instrument_id   VARCHAR(255) NOT NULL,   -- graph Entity.id / wallet_authorization PK
    instrument_type VARCHAR(20) NOT NULL CHECK (instrument_type IN ('FIAT_ACCOUNT', 'CRYPTO_WALLET')),
    party_id        VARCHAR(255) NOT NULL REFERENCES app.party(party_id),
    ownership_pct   NUMERIC(5,2) DEFAULT 100.00,
    valid_from      TIMESTAMPTZ,
    valid_to        TIMESTAMPTZ,             -- NULL = currently effective
    PRIMARY KEY (instrument_id, party_id)
);

CREATE TABLE IF NOT EXISTS app.party_ubo (
    subject_party_id VARCHAR(255) NOT NULL REFERENCES app.party(party_id),
    ubo_party_id     VARCHAR(255) NOT NULL REFERENCES app.party(party_id),
    ownership_pct    NUMERIC(5,2),
    control_role     VARCHAR(50),
    PRIMARY KEY (subject_party_id, ubo_party_id),
    CHECK (subject_party_id <> ubo_party_id)
);

CREATE INDEX IF NOT EXISTS idx_app_party_instrument_party ON app.party_instrument(party_id);

-- 2. Verified credentials held by a party
CREATE TABLE IF NOT EXISTS app.party_credential (
    credential_id    VARCHAR(255) PRIMARY KEY,  -- platform-side reference (never the raw credential)
    party_id         VARCHAR(255) NOT NULL REFERENCES app.party(party_id),
    vct              VARCHAR(100) NOT NULL,     -- hkt_kyc_v1 | hkt_licensed_institution_v1 | hkt_wallet_binding_v1 ...
    issuer_did       VARCHAR(255) NOT NULL,
    verified_at      TIMESTAMPTZ NOT NULL,
    expires_at       TIMESTAMPTZ,
    status           VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
                     CHECK (status IN ('ACTIVE', 'EXPIRED', 'REVOKED', 'REFRESH_DUE')),
    evidence_hash    VARCHAR(128),              -- digest of the verification response
    last_checked_at  TIMESTAMPTZ,
    claims           JSONB,                     -- minimal claim subset (masked at API layer)
    UNIQUE (party_id, vct, issuer_did)
);

CREATE INDEX IF NOT EXISTS idx_app_party_credential_status
    ON app.party_credential(status) WHERE status = 'ACTIVE';

-- 3. Authorized-wallet registry (one row per controlled address)
CREATE TABLE IF NOT EXISTS app.wallet_authorization (
    instrument_id      VARCHAR(255) PRIMARY KEY,
    blockchain         VARCHAR(30) NOT NULL
                       CHECK (blockchain IN ('ETHEREUM', 'POLYGON', 'SOLANA', 'TRON', 'OTHER')),
    wallet_address     VARCHAR(255) NOT NULL,
    address_proof      VARCHAR(20) NOT NULL
                       CHECK (address_proof IN ('SIGNATURE', 'MICRO_TX', 'ISSUER_ATTESTED')),
    proof_ref          VARCHAR(255),
    custody_type       VARCHAR(20)
                       CHECK (custody_type IN ('HOSTED', 'UNHOSTED', 'EXCHANGE_CUSTODIED', 'MULTI_SIG')),
    binding_credential VARCHAR(255) REFERENCES app.party_credential(credential_id),
    party_id           VARCHAR(255) REFERENCES app.party(party_id),
    authorized         BOOLEAN NOT NULL DEFAULT FALSE,
    authorized_from    TIMESTAMPTZ,
    authorized_until   TIMESTAMPTZ,             -- min(credential expiry, policy cap)
    authorized_by      VARCHAR(255),            -- maker
    approved_by        VARCHAR(255),            -- checker (maker-checker, TASK-040)
    UNIQUE (blockchain, wallet_address)
);

CREATE INDEX IF NOT EXISTS idx_app_wallet_authz_active
    ON app.wallet_authorization(authorized) WHERE authorized = TRUE;

-- 4. Dead-letter queue for the nightly re-verification batch (TASK-048)
CREATE TABLE IF NOT EXISTS app.credential_check_dlq (
    dlq_id       BIGSERIAL PRIMARY KEY,
    credential_id VARCHAR(255) NOT NULL,
    checked_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    reason       TEXT NOT NULL,
    detail       JSONB
);

-- 5. Privileges / RLS parity
GRANT ALL PRIVILEGES ON TABLE app.party, app.party_instrument, app.party_ubo,
    app.party_credential, app.wallet_authorization, app.credential_check_dlq TO aml_api_role;
GRANT USAGE ON SEQUENCE app.credential_check_dlq_dlq_id_seq TO aml_api_role;
GRANT SELECT ON app.party, app.party_instrument, app.party_ubo,
    app.party_credential, app.wallet_authorization TO aml_etl_role;

-- v5 migration map (kept beside the schema so it cannot drift):
--   app.party.did/onboarding_channel -> aml_core.party (enum parity incl. iAM_SMART)
--   app.party_credential             -> aml_core.account_party_link + credential columns
--   app.wallet_authorization         -> aml_core.account (blockchain_address, wallet_custody_type)
--                                        + party_wallet (is_verified, verification/proof refs)
