create schema if not exists app;

create table if not exists app.tenants (
  tenant_id uuid primary key default gen_random_uuid(),
  tenant_code text not null unique,
  tenant_name text not null,
  status text not null default 'active' check (status in ('active','inactive','suspended')),
  created_at timestamptz not null default now()
);

create table if not exists app.app_users (
  user_id uuid primary key default gen_random_uuid(),
  keycloak_user_id uuid not null unique,
  username text not null unique,
  email text not null unique,
  full_name text,
  status text not null default 'active' check (status in ('active','disabled','locked')),
  created_at timestamptz not null default now()
);

create table if not exists app.tenant_memberships (
  tenant_id uuid not null references app.tenants(tenant_id) on delete cascade,
  user_id uuid not null references app.app_users(user_id) on delete cascade,
  membership_status text not null default 'active' check (membership_status in ('active','invited','suspended')),
  joined_at timestamptz not null default now(),
  primary key (tenant_id, user_id)
);

create table if not exists app.roles (
  role_id uuid primary key default gen_random_uuid(),
  role_code text not null unique,
  role_name text not null,
  role_scope text not null check (role_scope in ('realm','tenant','case')),
  description text
);

create table if not exists app.permissions (
  permission_id uuid primary key default gen_random_uuid(),
  permission_code text not null unique,
  resource_type text not null,
  action text not null,
  description text
);

create table if not exists app.role_permissions (
  role_id uuid not null references app.roles(role_id) on delete cascade,
  permission_id uuid not null references app.permissions(permission_id) on delete cascade,
  primary key (role_id, permission_id)
);

create table if not exists app.user_tenant_roles (
  tenant_id uuid not null references app.tenants(tenant_id) on delete cascade,
  user_id uuid not null references app.app_users(user_id) on delete cascade,
  role_id uuid not null references app.roles(role_id) on delete cascade,
  granted_by uuid references app.app_users(user_id),
  granted_at timestamptz not null default now(),
  primary key (tenant_id, user_id, role_id)
);

create table if not exists app.alerts (
  alert_id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references app.tenants(tenant_id) on delete cascade,
  alert_type text not null,
  risk_score numeric(10,2),
  status text not null default 'open' check (status in ('open','triaged','escalated','closed')),
  customer_id text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  created_by uuid references app.app_users(user_id)
);

create table if not exists app.cases (
  case_id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references app.tenants(tenant_id) on delete cascade,
  case_number text not null unique,
  status text not null check (status in ('open','under_review','approved','filed','closed')),
  severity text not null check (severity in ('low','medium','high','critical')),
  source_alert_id uuid references app.alerts(alert_id),
  created_by uuid not null references app.app_users(user_id),
  assigned_to uuid references app.app_users(user_id),
  reviewer_id uuid references app.app_users(user_id),
  approver_id uuid references app.app_users(user_id),
  created_at timestamptz not null default now()
);

create table if not exists app.case_acl (
  case_id uuid not null references app.cases(case_id) on delete cascade,
  user_id uuid not null references app.app_users(user_id) on delete cascade,
  access_level text not null check (access_level in ('view','edit','review','approve')),
  granted_by uuid references app.app_users(user_id),
  granted_at timestamptz not null default now(),
  primary key (case_id, user_id, access_level)
);

create table if not exists app.audit_access_events (
  event_id uuid primary key default gen_random_uuid(),
  tenant_id uuid references app.tenants(tenant_id),
  user_id uuid references app.app_users(user_id),
  resource_type text not null,
  resource_id uuid,
  action text not null,
  decision text not null check (decision in ('allow','deny')),
  reason text,
  created_at timestamptz not null default now()
);
