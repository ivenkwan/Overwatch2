alter table app.alerts enable row level security;
alter table app.cases enable row level security;
alter table app.case_acl enable row level security;
alter table app.audit_access_events enable row level security;

alter table app.alerts force row level security;
alter table app.cases force row level security;
alter table app.case_acl force row level security;
alter table app.audit_access_events force row level security;

create policy alerts_tenant_isolation on app.alerts
using (tenant_id = current_setting('app.current_tenant')::uuid)
with check (tenant_id = current_setting('app.current_tenant')::uuid);

create policy cases_tenant_and_assignment on app.cases
using (
  tenant_id = current_setting('app.current_tenant')::uuid
  and (
    assigned_to = current_setting('app.current_user_id', true)::uuid
    or reviewer_id = current_setting('app.current_user_id', true)::uuid
    or approver_id = current_setting('app.current_user_id', true)::uuid
    or exists (
      select 1
      from app.user_tenant_roles utr
      join app.roles r on r.role_id = utr.role_id
      where utr.tenant_id = app.cases.tenant_id
        and utr.user_id = current_setting('app.current_user_id', true)::uuid
        and r.role_code in ('platform_admin','tenant_admin','aml_reviewer','aml_approver','auditor')
    )
    or exists (
      select 1
      from app.case_acl ca
      where ca.case_id = app.cases.case_id
        and ca.user_id = current_setting('app.current_user_id', true)::uuid
    )
  )
)
with check (tenant_id = current_setting('app.current_tenant')::uuid);

create policy case_acl_tenant_policy on app.case_acl
using (
  exists (
    select 1 from app.cases c
    where c.case_id = app.case_acl.case_id
      and c.tenant_id = current_setting('app.current_tenant')::uuid
  )
);

create policy audit_events_tenant_policy on app.audit_access_events
using (tenant_id = current_setting('app.current_tenant')::uuid)
with check (tenant_id = current_setting('app.current_tenant')::uuid);
