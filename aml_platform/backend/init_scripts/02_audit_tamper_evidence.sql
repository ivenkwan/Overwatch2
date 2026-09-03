-- 02_audit_tamper_evidence.sql
-- Create an append-only trigger and cryptographic hash chain for audit_access_events

-- 1. Function to prevent UPDATE and DELETE
CREATE OR REPLACE FUNCTION app.prevent_audit_tampering()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' OR TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'audit_access_events is an append-only table. Tampering (UPDATE/DELETE) is strictly prohibited.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_audit_tampering
BEFORE UPDATE OR DELETE ON app.audit_access_events
FOR EACH ROW EXECUTE FUNCTION app.prevent_audit_tampering();

-- 2. Function to compute cryptographic hash chain
CREATE OR REPLACE FUNCTION app.hash_audit_event()
RETURNS TRIGGER AS $$
DECLARE
    prev_hash TEXT;
    payload TEXT;
BEGIN
    -- Get the hash of the most recently inserted row
    SELECT record_hash INTO prev_hash
    FROM app.audit_access_events
    ORDER BY created_at DESC
    LIMIT 1;

    IF prev_hash IS NULL THEN
        prev_hash := 'genesis';
    END IF;

    -- Concatenate fields and previous hash
    payload := prev_hash || COALESCE(NEW.tenant_id::TEXT, '') || COALESCE(NEW.user_id::TEXT, '') || NEW.resource_type || COALESCE(NEW.resource_id::TEXT, '') || NEW.action || NEW.decision || COALESCE(NEW.reason, '') || NEW.created_at::TEXT;
    
    -- Calculate SHA-256 hash
    NEW.previous_hash := prev_hash;
    NEW.record_hash := encode(digest(payload, 'sha256'), 'hex');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_hash_audit_event
BEFORE INSERT ON app.audit_access_events
FOR EACH ROW EXECUTE FUNCTION app.hash_audit_event();
