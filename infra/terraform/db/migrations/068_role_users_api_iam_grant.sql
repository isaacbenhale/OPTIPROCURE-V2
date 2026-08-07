-- Liaison du rôle Postgres users_api_role au rôle IAM lambda_users_api.
-- Placeholder substitué à l'exécution par la Lambda de migration (variable
-- USERS_API_ROLE_ARN, voir infra/terraform/lambda_migrate.tf et
-- lambda_src/migrate/handler.py).
AWS IAM GRANT users_api_role TO '__USERS_API_ROLE_ARN__';
