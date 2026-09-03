insert into app.tenants (tenant_id, tenant_code, tenant_name)
values ('11111111-1111-1111-1111-111111111111','bank-hk-01','Sample HK Wallet Institution')
on conflict (tenant_code) do nothing;

insert into app.app_users (user_id, keycloak_user_id, username, email, full_name)
values
('21111111-1111-1111-1111-111111111111','31111111-1111-1111-1111-111111111111','alice.investigator','alice@example.com','Alice Investigator'),
('22222222-2222-2222-2222-222222222222','32222222-2222-2222-2222-222222222222','bob.reviewer','bob@example.com','Bob Reviewer'),
('23333333-3333-3333-3333-333333333333','33333333-3333-3333-3333-333333333333','cara.approver','cara@example.com','Cara Approver')
on conflict (username) do nothing;

insert into app.tenant_memberships (tenant_id, user_id)
values
('11111111-1111-1111-1111-111111111111','21111111-1111-1111-1111-111111111111'),
('11111111-1111-1111-1111-111111111111','22222222-2222-2222-2222-222222222222'),
('11111111-1111-1111-1111-111111111111','23333333-3333-3333-3333-333333333333')
on conflict do nothing;

insert into app.user_tenant_roles (tenant_id, user_id, role_id)
select '11111111-1111-1111-1111-111111111111', '21111111-1111-1111-1111-111111111111', role_id from app.roles where role_code = 'aml_investigator'
on conflict do nothing;

insert into app.user_tenant_roles (tenant_id, user_id, role_id)
select '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', role_id from app.roles where role_code = 'aml_reviewer'
on conflict do nothing;

insert into app.user_tenant_roles (tenant_id, user_id, role_id)
select '11111111-1111-1111-1111-111111111111', '23333333-3333-3333-3333-333333333333', role_id from app.roles where role_code = 'aml_approver'
on conflict do nothing;
