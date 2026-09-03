-- Set these at the start of each authenticated request/transaction.
set app.current_tenant = '11111111-1111-1111-1111-111111111111';
set app.current_user_id = '21111111-1111-1111-1111-111111111111';

select app.user_has_permission(
  current_setting('app.current_user_id')::uuid,
  current_setting('app.current_tenant')::uuid,
  'cases.create'
);
