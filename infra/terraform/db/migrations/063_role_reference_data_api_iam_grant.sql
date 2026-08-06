-- Liaison du rôle Postgres reference_data_api_role au rôle IAM
-- lambda_reference_data_api. Placeholder substitué à l'exécution par la
-- Lambda de migration (variable REFERENCE_DATA_API_ROLE_ARN, voir
-- infra/terraform/lambda_migrate.tf et lambda_src/migrate/handler.py).
AWS IAM GRANT reference_data_api_role TO '__REFERENCE_DATA_API_ROLE_ARN__';
