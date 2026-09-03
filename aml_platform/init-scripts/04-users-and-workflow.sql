-- 1. Enable pgcrypto for password hashing
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2. Create User Role Enum
CREATE TYPE user_role AS ENUM ('JUNIOR_ANALYST', 'SENIOR_INVESTIGATOR', 'DEPARTMENT_HEAD', 'ADMIN');

-- 3. Create Users Table
CREATE TABLE IF NOT EXISTS public.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'JUNIOR_ANALYST',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Seed Default Users
-- Default password for all seed users is 'password123'
INSERT INTO public.users (username, email, hashed_password, role) VALUES
('junior_01', 'junior1@aml.local', crypt('password123', gen_salt('bf')), 'JUNIOR_ANALYST'),
('senior_01', 'senior1@aml.local', crypt('password123', gen_salt('bf')), 'SENIOR_INVESTIGATOR'),
('head_01', 'head1@aml.local', crypt('password123', gen_salt('bf')), 'DEPARTMENT_HEAD'),
('admin_01', 'admin1@aml.local', crypt('password123', gen_salt('bf')), 'ADMIN')
ON CONFLICT (username) DO NOTHING;

-- 5. Alter Alerts Table for Case Management Workflow
ALTER TABLE ag_catalog.alerts ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'OPEN';
ALTER TABLE ag_catalog.alerts ADD COLUMN IF NOT EXISTS assigned_to INTEGER REFERENCES public.users(id);
ALTER TABLE ag_catalog.alerts ADD COLUMN IF NOT EXISTS maker_id INTEGER REFERENCES public.users(id);
ALTER TABLE ag_catalog.alerts ADD COLUMN IF NOT EXISTS checker_id INTEGER REFERENCES public.users(id);
ALTER TABLE ag_catalog.alerts ADD COLUMN IF NOT EXISTS resolution_notes TEXT;
ALTER TABLE ag_catalog.alerts ADD COLUMN IF NOT EXISTS checker_notes TEXT;

-- 6. Indexes for Performance (as proposed by Skeptic)
CREATE INDEX IF NOT EXISTS idx_alerts_status ON ag_catalog.alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_assigned_to ON ag_catalog.alerts(assigned_to);
