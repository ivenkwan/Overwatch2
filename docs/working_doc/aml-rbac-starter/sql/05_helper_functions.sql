create or replace function app.user_has_permission(
  p_user_id uuid,
  p_tenant_id uuid,
  p_permission_code text
) returns boolean
language sql
stable
as $$
  select exists (
    select 1
    from app.user_tenant_roles utr
    join app.role_permissions rp on rp.role_id = utr.role_id
    join app.permissions p on p.permission_id = rp.permission_id
    where utr.user_id = p_user_id
      and utr.tenant_id = p_tenant_id
      and p.permission_code = p_permission_code
  );
$$;

create or replace function app.log_access_decision(
  p_tenant_id uuid,
  p_user_id uuid,
  p_resource_type text,
  p_resource_id uuid,
  p_action text,
  p_decision text,
  p_reason text
) returns void
language sql
as $$
  insert into app.audit_access_events(
    tenant_id, user_id, resource_type, resource_id, action, decision, reason
  ) values (
    p_tenant_id, p_user_id, p_resource_type, p_resource_id, p_action, p_decision, p_reason
  );
$$;
