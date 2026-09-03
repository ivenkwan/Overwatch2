# Composite role plan

Create these composite roles after importing the realm JSON:

## Realm-level composites
- `aml_platform_superuser` = `platform_admin` + `compliance_officer` + `auditor`

## Client-level composites on `aml-api`
- `aml_investigator` = `dashboard.view`, `alerts.view`, `alerts.triage`, `cases.view`, `cases.create`, `cases.edit`, `evidence.upload`, `graph.view`, `graph.expand`
- `aml_reviewer` = `dashboard.view`, `alerts.view`, `alerts.escalate`, `cases.view`, `cases.review`, `screening.view`, `screening.review`, `str.create`
- `aml_approver` = `dashboard.view`, `cases.view`, `cases.approve`, `cases.close`, `str.approve`
- `aml_auditor` = `dashboard.view`, `alerts.view`, `cases.view`, `screening.view`, `rules.view`
- `tenant_admin_app` = `dashboard.view`, `alerts.view`, `cases.view`, `cases.assign`, `users.view`, `users.manage`, `rbac.manage`, `rules.view`, `str.create`
- `platform_admin_app` = all aml-api client roles

## Notes
- Keep tenant assignment in PostgreSQL, not just in Keycloak.
- Put `tenant_id` on the user as an attribute only when a user is single-tenant; for multi-tenant users, resolve active tenant in the application and set PostgreSQL session context explicitly.
- Use Keycloak for authentication and coarse role identity, PostgreSQL for effective tenant- and case-scoped authorization.
