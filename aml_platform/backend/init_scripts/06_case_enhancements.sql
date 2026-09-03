-- 06_case_enhancements.sql (TASK-015 / TASK-017)
-- Case-management enhancements:
--   * case_notes          — free-form notes with attachments metadata
--   * workflow_event      — every workflow (Flowable) state transition is
--                           tracked in the DB (dual-state, Lesson 5), so
--                           instances are observable and stale/failed
--                           workflows can be surfaced to operators
--                           (TASK-017)
--   * timeline derives from audit_access_events + workflow_event (no extra
--     table needed — events ARE the timeline)

CREATE TABLE IF NOT EXISTS app.case_notes (
    note_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id      UUID NOT NULL REFERENCES app.cases(case_id) ON DELETE CASCADE,
    author_id    UUID REFERENCES app.app_users(user_id),
    body         TEXT NOT NULL,
    attachment_name TEXT,                 -- metadata only; content lives in
    attachment_ref  TEXT,                 -- the object store (see note in
                                          -- 01_rbac / SECURITY.md: writes are
                                          -- literal-path confined, so uploads
                                          -- are deferred to the store layer)
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_case_notes_case ON app.case_notes(case_id, created_at);

CREATE TABLE IF NOT EXISTS app.workflow_event (
    event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id         UUID NOT NULL REFERENCES app.cases(case_id) ON DELETE CASCADE,
    workflow_instance_id TEXT NOT NULL,
    task_key        TEXT,
    event_type      TEXT NOT NULL,        -- started | task_completed | completed | failed
    detail          JSONB,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workflow_event_case ON app.workflow_event(case_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_workflow_event_instance ON app.workflow_event(workflow_instance_id);

-- Per-instance tracking: record when a workflow instance ends (completed or
-- failed) so operators can query for instances left mid-flight.
ALTER TABLE app.cases ADD COLUMN IF NOT EXISTS workflow_status TEXT
    CHECK (workflow_status IN ('running', 'completed', 'failed'));

GRANT ALL PRIVILEGES ON TABLE app.case_notes TO aml_api_role;
GRANT ALL PRIVILEGES ON TABLE app.workflow_event TO aml_api_role;
