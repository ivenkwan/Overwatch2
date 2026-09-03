-- 06_alert_feed_indexes.sql (TASK-012)
-- Server-side filtering needs supporting indexes: the monitoring feed sorts
-- by txn_date and filters by amount/type. The alert table (once it exists
-- in the deployed schema) gets the same treatment via the second block.

CREATE INDEX IF NOT EXISTS idx_core_transactions_txn_date
    ON core.transactions (txn_date DESC);
CREATE INDEX IF NOT EXISTS idx_core_transactions_type_date
    ON core.transactions (txn_type, txn_date DESC);

-- app.alerts filter columns (deployed alert table). Column sets vary by DB
-- shape, so each index is created only when its column exists.
CREATE INDEX IF NOT EXISTS idx_app_alerts_status_created
    ON app.alerts (status, created_at DESC);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = 'app' AND table_name = 'alerts'
                 AND column_name = 'severity') THEN
        CREATE INDEX IF NOT EXISTS idx_app_alerts_severity
            ON app.alerts (severity);
    END IF;
END
$$;
