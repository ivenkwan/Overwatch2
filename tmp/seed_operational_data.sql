-- 1. Insert tenant and user if not exists
INSERT INTO app.tenants (tenant_id, tenant_code, tenant_name)
VALUES ('e34743fc-2b36-4076-96b0-7bd7332c9183', 'default_tenant', 'Default Overwatch Tenant')
ON CONFLICT (tenant_code) DO NOTHING;

INSERT INTO app.app_users (user_id, keycloak_user_id, username, email, full_name)
VALUES ('5b62b160-c3d3-4a11-85e6-6705db85e13d', '00000000-0000-0000-0000-000000000000', 'junior_01', 'junior1@aml.local', 'Junior Analyst')
ON CONFLICT (username) DO NOTHING;

-- Clean existing demo alerts/cases to avoid duplicate bloat
DELETE FROM app.cases WHERE tenant_id = 'e34743fc-2b36-4076-96b0-7bd7332c9183';
DELETE FROM app.alerts WHERE tenant_id = 'e34743fc-2b36-4076-96b0-7bd7332c9183';

-- 2. Insert dummy alerts for yesterday (2026-06-01)
-- Insert 80 closed alerts
INSERT INTO app.alerts (tenant_id, alert_type, risk_score, status, customer_id, payload, created_at, created_by)
SELECT 
    'e34743fc-2b36-4076-96b0-7bd7332c9183',
    'TRANSACTION_MONITORING',
    random() * 60,
    'closed',
    'C' || floor(10000 + random() * 90000)::text,
    '{"reason": "Cleared by low risk profile"}'::jsonb,
    '2026-06-01 10:00:00'::timestamp,
    '5b62b160-c3d3-4a11-85e6-6705db85e13d'
FROM generate_series(1, 80);

-- Insert 20 escalated alerts
INSERT INTO app.alerts (tenant_id, alert_type, risk_score, status, customer_id, payload, created_at, created_by)
SELECT 
    'e34743fc-2b36-4076-96b0-7bd7332c9183',
    'TRANSACTION_MONITORING',
    80 + random() * 20,
    'escalated',
    'C' || floor(10000 + random() * 90000)::text,
    '{"reason": "Escalated due to suspicious structuring activity"}'::jsonb,
    '2026-06-01 12:00:00'::timestamp,
    '5b62b160-c3d3-4a11-85e6-6705db85e13d'
FROM generate_series(1, 20);

-- Insert 24 open alerts
INSERT INTO app.alerts (tenant_id, alert_type, risk_score, status, customer_id, payload, created_at, created_by)
SELECT 
    'e34743fc-2b36-4076-96b0-7bd7332c9183',
    'TRANSACTION_MONITORING',
    50 + random() * 30,
    'open',
    'C' || floor(10000 + random() * 90000)::text,
    '{"reason": "Awaiting primary review"}'::jsonb,
    '2026-06-01 14:00:00'::timestamp,
    '5b62b160-c3d3-4a11-85e6-6705db85e13d'
FROM generate_series(1, 24);

-- 2b. Insert dummy alerts for today (2026-06-02)
-- Insert 80 closed alerts
INSERT INTO app.alerts (tenant_id, alert_type, risk_score, status, customer_id, payload, created_at, created_by)
SELECT 
    'e34743fc-2b36-4076-96b0-7bd7332c9183',
    'TRANSACTION_MONITORING',
    random() * 60,
    'closed',
    'C' || floor(10000 + random() * 90000)::text,
    '{"reason": "Cleared by low risk profile"}'::jsonb,
    '2026-06-02 10:00:00'::timestamp,
    '5b62b160-c3d3-4a11-85e6-6705db85e13d'
FROM generate_series(1, 80);

-- Insert 20 escalated alerts
INSERT INTO app.alerts (tenant_id, alert_type, risk_score, status, customer_id, payload, created_at, created_by)
SELECT 
    'e34743fc-2b36-4076-96b0-7bd7332c9183',
    'TRANSACTION_MONITORING',
    80 + random() * 20,
    'escalated',
    'C' || floor(10000 + random() * 90000)::text,
    '{"reason": "Escalated due to suspicious structuring activity"}'::jsonb,
    '2026-06-02 12:00:00'::timestamp,
    '5b62b160-c3d3-4a11-85e6-6705db85e13d'
FROM generate_series(1, 20);

-- Insert 24 open alerts
INSERT INTO app.alerts (tenant_id, alert_type, risk_score, status, customer_id, payload, created_at, created_by)
SELECT 
    'e34743fc-2b36-4076-96b0-7bd7332c9183',
    'TRANSACTION_MONITORING',
    50 + random() * 30,
    'open',
    'C' || floor(10000 + random() * 90000)::text,
    '{"reason": "Awaiting primary review"}'::jsonb,
    '2026-06-02 14:00:00'::timestamp,
    '5b62b160-c3d3-4a11-85e6-6705db85e13d'
FROM generate_series(1, 24);

-- 3. Insert some dummy cases for those escalated alerts
INSERT INTO app.cases (tenant_id, case_number, status, severity, source_alert_id, created_by, created_at)
SELECT 
    'e34743fc-2b36-4076-96b0-7bd7332c9183',
    'CASE-' || (100000 + i)::text,
    'under_review',
    'high',
    (SELECT alert_id FROM app.alerts WHERE status = 'escalated' AND created_at::date = '2026-06-01' LIMIT 1 OFFSET (i - 1)),
    '5b62b160-c3d3-4a11-85e6-6705db85e13d',
    '2026-06-01 15:00:00'::timestamp
FROM generate_series(1, 15) i;

INSERT INTO app.cases (tenant_id, case_number, status, severity, source_alert_id, created_by, created_at)
SELECT 
    'e34743fc-2b36-4076-96b0-7bd7332c9183',
    'CASE-' || (200000 + i)::text,
    'under_review',
    'high',
    (SELECT alert_id FROM app.alerts WHERE status = 'escalated' AND created_at::date = '2026-06-02' LIMIT 1 OFFSET (i - 1)),
    '5b62b160-c3d3-4a11-85e6-6705db85e13d',
    '2026-06-02 15:00:00'::timestamp
FROM generate_series(1, 15) i;
