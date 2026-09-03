insert into app.roles (role_code, role_name, role_scope, description) values
('platform_admin','Platform Administrator','realm','Full cross-tenant platform administration'),
('tenant_admin','Tenant Administrator','tenant','Tenant-scoped administration and user management'),
('aml_investigator','AML Investigator','tenant','Investigates alerts and cases'),
('aml_reviewer','AML Reviewer','tenant','Reviews escalations and prepares STRs'),
('aml_approver','AML Approver','tenant','Approves case closure and STR submission'),
('auditor','Auditor','tenant','Read-only audit access'),
('case_restricted_viewer','Restricted Case Viewer','case','Explicit case-level access only')
on conflict (role_code) do nothing;

insert into app.permissions (permission_code, resource_type, action, description) values
('dashboard.view','dashboard','view','View dashboard'),
('alerts.view','alert','view','View alerts'),
('alerts.triage','alert','triage','Triage alerts'),
('alerts.escalate','alert','escalate','Escalate alerts to cases'),
('cases.view','case','view','View cases'),
('cases.create','case','create','Create cases'),
('cases.assign','case','assign','Assign cases'),
('cases.edit','case','edit','Edit case details'),
('cases.review','case','review','Review cases'),
('cases.approve','case','approve','Approve cases'),
('cases.close','case','close','Close cases'),
('evidence.upload','evidence','upload','Upload investigation evidence'),
('graph.view','graph','view','View graph workspace'),
('graph.expand','graph','expand','Expand entity neighborhoods'),
('screening.view','screening','view','View screening results'),
('screening.review','screening','review','Review screening hits'),
('str.create','str','create','Draft suspicious transaction reports'),
('str.approve','str','approve','Approve suspicious transaction reports'),
('users.view','user','view','View users'),
('users.manage','user','manage','Manage users'),
('rbac.manage','rbac','manage','Manage role assignments'),
('rules.view','rule','view','View rules'),
('rules.manage','rule','manage','Manage rules'),
('etl.monitor','etl','monitor','Monitor ETL jobs')
on conflict (permission_code) do nothing;

with rp(role_code, permission_code) as (
  values
  ('platform_admin','dashboard.view'),('platform_admin','alerts.view'),('platform_admin','alerts.triage'),('platform_admin','alerts.escalate'),
  ('platform_admin','cases.view'),('platform_admin','cases.create'),('platform_admin','cases.assign'),('platform_admin','cases.edit'),
  ('platform_admin','cases.review'),('platform_admin','cases.approve'),('platform_admin','cases.close'),('platform_admin','evidence.upload'),
  ('platform_admin','graph.view'),('platform_admin','graph.expand'),('platform_admin','screening.view'),('platform_admin','screening.review'),
  ('platform_admin','str.create'),('platform_admin','str.approve'),('platform_admin','users.view'),('platform_admin','users.manage'),
  ('platform_admin','rbac.manage'),('platform_admin','rules.view'),('platform_admin','rules.manage'),('platform_admin','etl.monitor'),
  ('tenant_admin','dashboard.view'),('tenant_admin','alerts.view'),('tenant_admin','cases.view'),('tenant_admin','cases.assign'),
  ('tenant_admin','users.view'),('tenant_admin','users.manage'),('tenant_admin','rbac.manage'),('tenant_admin','rules.view'),('tenant_admin','str.create'),
  ('aml_investigator','dashboard.view'),('aml_investigator','alerts.view'),('aml_investigator','alerts.triage'),('aml_investigator','cases.view'),
  ('aml_investigator','cases.create'),('aml_investigator','cases.edit'),('aml_investigator','evidence.upload'),('aml_investigator','graph.view'),('aml_investigator','graph.expand'),
  ('aml_reviewer','dashboard.view'),('aml_reviewer','alerts.view'),('aml_reviewer','alerts.escalate'),('aml_reviewer','cases.view'),
  ('aml_reviewer','cases.review'),('aml_reviewer','screening.view'),('aml_reviewer','screening.review'),('aml_reviewer','str.create'),
  ('aml_approver','dashboard.view'),('aml_approver','cases.view'),('aml_approver','cases.approve'),('aml_approver','cases.close'),('aml_approver','str.approve'),
  ('auditor','dashboard.view'),('auditor','alerts.view'),('auditor','cases.view'),('auditor','screening.view'),('auditor','rules.view'),
  ('case_restricted_viewer','cases.view')
)
insert into app.role_permissions (role_id, permission_id)
select r.role_id, p.permission_id
from rp
join app.roles r on r.role_code = rp.role_code
join app.permissions p on p.permission_code = rp.permission_code
on conflict do nothing;
